from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import connectors_sciencebase as sciencebase  # noqa: E402
from app.services.connector_egress_transport import (  # noqa: E402
    BoundedConnectorResponse,
)


LIVE_STORAGE_KEY = (
    "__disk__7e/49/e8/7e49e8a4a53eb2219837f97defb22a25a286cdbc"
)
LIVE_DOWNLOAD_URI = (
    "https://www.sciencebase.gov/catalog/file/get/"
    f"{sciencebase.SCIENCEBASE_FRESH_ITEM_ID}?f="
    "__disk__7e%2F49%2Fe8%2F7e49e8a4a53eb2219837f97defb22a25a286cdbc"
)


def _live_file_entry() -> dict[str, Any]:
    return {
        "cuid": None,
        "key": None,
        "bucket": None,
        "published": False,
        "node": None,
        "name": sciencebase.SCIENCEBASE_FRESH_FILE_NAME,
        "title": None,
        "contentType": "text/csv",
        "contentEncoding": None,
        "pathOnDisk": LIVE_STORAGE_KEY,
        "processed": False,
        "processToken": None,
        "imageWidth": None,
        "imageHeight": None,
        "size": 510,
        "dateUploaded": "2023-01-25T21:48:54Z",
        "originalMetadata": False,
        "useForPreview": False,
        "movedToS3": False,
        "s3Object": None,
        "checksum": None,
        "url": LIVE_DOWNLOAD_URI,
        "downloadUri": LIVE_DOWNLOAD_URI,
        "viewUri": LIVE_DOWNLOAD_URI + "&allowOpen=true",
    }


def _hydration_response(entry: dict[str, Any]) -> BoundedConnectorResponse:
    body = json.dumps({"files": [entry]}).encode("utf-8")
    return BoundedConnectorResponse(
        outcome_class="completed",
        response_status=200,
        safe_headers={"content_type": "application/json"},
        body=body,
        body_sha256=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        location_values=(),
        counted_status_header_bytes=32,
        delivered_body_bytes=len(body),
    )


def test_live_file_entry_uses_validated_download_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validated: list[str] = []
    validator = sciencebase._validate_fresh_sciencebase_url

    def record_validation(raw_url: str) -> dict[str, Any]:
        validated.append(raw_url)
        return validator(raw_url)

    monkeypatch.setattr(
        sciencebase,
        "_validate_fresh_sciencebase_url",
        record_validation,
    )

    raw_url, projection = sciencebase._parse_fresh_sciencebase_hydration(
        _hydration_response(_live_file_entry())
    )

    assert raw_url == LIVE_DOWNLOAD_URI
    assert validated == [LIVE_DOWNLOAD_URI]
    assert (
        projection["artifact_request_class"]["query_class"]
        == "exact_single_f_pinned_storage_key"
    )


def test_conflicting_url_metadata_is_not_a_second_locator() -> None:
    entry = _live_file_entry()
    entry["url"] = (
        "https://evil.example/catalog/file/get/"
        f"{sciencebase.SCIENCEBASE_FRESH_ITEM_ID}?f=other.csv"
    )

    with pytest.raises(
        sciencebase.ScienceBaseFreshAcquisitionError,
        match="sciencebase_exact_file_locator_invalid",
    ):
        sciencebase._parse_fresh_sciencebase_hydration(
            _hydration_response(entry)
        )


@pytest.mark.parametrize(
    "raw_url",
    [
        LIVE_DOWNLOAD_URI.replace("www.sciencebase.gov", "evil.example"),
        LIVE_DOWNLOAD_URI[:-1] + "d",
        LIVE_DOWNLOAD_URI.replace("%2F", "/", 1),
        LIVE_DOWNLOAD_URI.replace("%2F", "%2f", 1),
        LIVE_DOWNLOAD_URI + "&x=1",
    ],
)
def test_storage_key_locator_rejects_unpinned_or_noncanonical_forms(
    raw_url: str,
) -> None:
    with pytest.raises(
        sciencebase.ScienceBaseFreshAcquisitionError,
        match="sciencebase_artifact_url_invalid",
    ):
        sciencebase._validate_fresh_sciencebase_url(raw_url)
