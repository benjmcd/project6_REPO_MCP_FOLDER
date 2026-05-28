from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.layer3_sec_edgar_ref_safety import (  # noqa: E402
    contains_forbidden_ref,
    contains_forbidden_ref_tree,
    find_forbidden_ref_paths,
)


def test_sec_edgar_ref_safety_blocks_raw_urls_and_local_paths() -> None:
    blocked = (
        "https://www.sec.gov/Archives/example",
        "file://local/source",
        "s3://bucket/source",
        r"C:\Users\benny\source.htm",
        r"\\server\share\source.htm",
        "//server/share/source.htm",
        "/tmp/source.htm",
        "raw path = D:/storage/source.htm",
    )

    for value in blocked:
        assert contains_forbidden_ref(value), value


def test_sec_edgar_ref_safety_allows_hashes_qnames_and_dates() -> None:
    allowed = (
        "abc123def456",
        "us-gaap:Revenue",
        "iso4217:USD",
        "2025-12-31",
        "sec-edgar-html-inline-xbrl-parser-aaaaaaaaaaaaaaaaaaaaaaaa",
        "sec-edgar-text-table-authority-envelope://sec-edgar-text-table-authority-envelope-abc123/def456",
        "USD/share",
    )

    for value in allowed:
        assert not contains_forbidden_ref(value), value


def test_sec_edgar_ref_safety_finds_nested_forbidden_request_fields() -> None:
    payload = {
        "client_request_id": "safe",
        "nested": {
            "source": [{"value": "safe"}, {"value": "https://www.sec.gov/raw"}],
            "local_path": "redacted-by-field-name",
        },
        "items": [{"artifact": r"C:\raw\source.htm"}],
    }

    assert contains_forbidden_ref_tree(payload)
    assert find_forbidden_ref_paths(payload, forbidden_keys={"local_path"}) == [
        "items[0].artifact",
        "nested.local_path",
        "nested.source[1].value",
    ]
