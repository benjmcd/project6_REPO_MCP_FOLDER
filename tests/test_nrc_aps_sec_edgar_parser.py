import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_sec_edgar_parser  # noqa: E402


def _filing_bytes(*, form_type: str = "10-K", document_text: str | None = None) -> bytes:
    body = document_text or """
ITEM 1. Business
Registrant manufactures industrial widgets.

<TABLE>
date|revenue|segment
2026-01-01|42|alpha
2026-01-02|43|beta
</TABLE>

ITEM 7. Management Discussion
Revenue increased in the period.
"""
    return f"""<SEC-DOCUMENT>0000320193-24-000123.txt : 20241101
<SEC-HEADER>
<ACCESSION-NUMBER>0000320193-24-000123
<CONFORMED-SUBMISSION-TYPE>{form_type}
<FILED-AS-OF-DATE>20241101
<COMPANY-CONFORMED-NAME>EXAMPLE INDUSTRIES INC
<CENTRAL-INDEX-KEY>0000320193
<PUBLIC-DOCUMENT-COUNT>1
</SEC-HEADER>
<DOCUMENT>
<TYPE>{form_type}
<SEQUENCE>1
<FILENAME>example-20241101.txt
<DESCRIPTION>Primary filing document
<TEXT>
{body}
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
""".encode("utf-8")


def test_parse_sec_edgar_filing_extracts_metadata_sections_and_table_units():
    result = nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(content=_filing_bytes())

    assert result["sec_edgar_filing_contract_id"] == "aps_sec_edgar_filing_units_v1"
    assert result["filing_metadata"]["accession_number"] == "0000320193-24-000123"
    assert result["filing_metadata"]["form_type"] == "10-K"
    assert result["filing_metadata"]["company_conformed_name"] == "EXAMPLE INDUSTRIES INC"
    assert result["document_count"] == 1
    assert [unit["section_label"] for unit in result["ordered_units"]] == ["ITEM 1", "ITEM 7"]
    assert result["table_count"] == 1
    assert result["table_units"][0]["table_source"] == "sec_edgar_table_block"
    assert result["table_units"][0]["row_count"] == 2
    assert result["table_units"][0]["columns"][1]["name"] == "revenue"
    assert result["time_series_units"][0]["time_column"] == "date"
    assert "industrial widgets" in result["normalized_text"]


def test_parse_sec_edgar_filing_without_table_still_emits_document_sections():
    result = nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(
        content=_filing_bytes(document_text="ITEM 1. Business\nNarrative only filing text.")
    )

    assert result["section_count"] == 1
    assert result["table_count"] == 0
    assert result["table_units"] == []
    assert result["ordered_units"][0]["text"].startswith("ITEM 1. Business")


def test_parse_sec_edgar_filing_rejects_unsupported_form_type():
    with pytest.raises(ValueError, match="sec_edgar_form_type_not_admitted"):
        nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(content=_filing_bytes(form_type="SC 13G"))


def test_parse_sec_edgar_filing_rejects_html_document_text():
    with pytest.raises(ValueError, match="sec_edgar_html_document_not_admitted"):
        nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(
            content=_filing_bytes(document_text="<html><body>Inline HTML</body></html>")
        )


def test_parse_sec_edgar_filing_rejects_missing_submission_signature():
    with pytest.raises(ValueError, match="sec_edgar_signature_missing"):
        nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(content=b"ITEM 1. Plain text without EDGAR wrapper")


def test_parse_sec_edgar_filing_rejects_malformed_table_block():
    with pytest.raises(ValueError, match="sec_edgar_table_parse_failed"):
        nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(
            content=_filing_bytes(document_text="ITEM 1. Business\n<TABLE>\nnot a table\n</TABLE>")
        )
