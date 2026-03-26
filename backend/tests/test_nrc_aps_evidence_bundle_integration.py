"""Tests for evidence bundle integration with visual artifacts and document-level provenance.

Verifies that visual_page_refs, document_class, media_type, page_count, and
diagnostics_ref flow through:
  1. _serialize_index_row()  ->  serialized dict
  2. _index_signature()      ->  checksum sensitivity
  3. grouped_page()          ->  group assembly
  4. Pydantic schemas        ->  API response validation

Also covers chunk-level fields (page_start, page_end, unit_kind, quality_status)
that were previously silently stripped.
"""

import json
import unittest
from typing import Any
from unittest.mock import MagicMock

from app.schemas.api import NrcApsEvidenceChunkOut, NrcApsEvidenceGroupOut
from app.services import nrc_aps_evidence_bundle_contract as contract
from app.services.nrc_aps_evidence_bundle import _index_signature, _serialize_index_row


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_linkage(**overrides: Any) -> MagicMock:
    defaults = {
        "content_id": "cid-001",
        "run_id": "run-001",
        "target_id": "tgt-001",
        "accession_number": "ML992800054",
        "content_contract_id": "aps_content_v1",
        "chunking_contract_id": "aps_chunking_v1",
        "content_units_ref": "nrc_adams_aps/content_units/sha256/ab/cd/abcd.json",
        "normalized_text_ref": "nrc_adams_aps/normalized/sha256/ef/01/ef01.txt",
        "blob_ref": "nrc_adams_aps/blobs/sha256/12/34/1234.pdf",
        "download_exchange_ref": "nrc_adams_aps/exchanges/sha256/56/78/5678.json",
        "discovery_ref": "nrc_adams_aps/discovery/sha256/9a/bc/9abc.json",
        "selection_ref": None,
        "normalized_text_sha256": "ef01" + "0" * 60,
        "blob_sha256": "1234" + "0" * 60,
        "diagnostics_ref": "nrc_adams_aps/diagnostics/sha256/de/ad/dead.json",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_document(**overrides: Any) -> MagicMock:
    defaults = {
        "normalization_contract_id": "aps_norm_v1",
        "normalized_text_sha256": "ef01" + "0" * 60,
        "updated_at": None,
        "visual_page_refs_json": json.dumps([{
            "page_number": 1,
            "visual_page_class": "diagram_or_visual",
            "status": "preserved",
            "width": 612.0,
            "height": 792.0,
            "visual_artifact_ref": "nrc_adams_aps/visual_pages/sha256/ab/cd/specimen.png",
            "visual_artifact_sha256": "abcd" + "0" * 60,
            "visual_artifact_dpi": 200,
            "visual_artifact_format": "png",
            "visual_artifact_semantics": "whole_page_rasterization",
        }]),
        "document_class": "inspection_report",
        "media_type": "application/pdf",
        "page_count": 12,
        "diagnostics_ref": "nrc_adams_aps/diagnostics/sha256/ff/00/ff00.json",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_chunk(**overrides: Any) -> MagicMock:
    defaults = {
        "chunk_id": "chunk-001",
        "chunk_ordinal": 0,
        "start_char": 0,
        "end_char": 500,
        "chunk_text": "The inspection identified no safety concerns.",
        "chunk_text_sha256": "aa" * 32,
        "updated_at": None,
        "page_start": 3,
        "page_end": 4,
        "unit_kind": "pdf_paragraph",
        "quality_status": "usable",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_serialized_row(**overrides: Any) -> dict[str, Any]:
    """Build a serialized row dict matching _serialize_index_row output shape."""
    row = _serialize_index_row(
        linkage=_make_linkage(),
        document=_make_document(),
        chunk=_make_chunk(),
    )
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# 1. _serialize_index_row tests
# ---------------------------------------------------------------------------

class TestSerializeIndexRow(unittest.TestCase):
    """Verify that _serialize_index_row captures all document-level and
    chunk-level provenance fields from the ORM objects."""

    def test_document_level_fields_present(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(),
            chunk=_make_chunk(),
        )
        self.assertEqual(row["document_class"], "inspection_report")
        self.assertEqual(row["media_type"], "application/pdf")
        self.assertEqual(row["page_count"], 12)
        self.assertIsNotNone(row["diagnostics_ref"])
        self.assertIsInstance(row["visual_page_refs"], list)
        self.assertEqual(len(row["visual_page_refs"]), 1)
        self.assertEqual(row["visual_page_refs"][0]["visual_artifact_dpi"], 200)

    def test_chunk_level_fields_present(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(),
            chunk=_make_chunk(),
        )
        self.assertEqual(row["page_start"], 3)
        self.assertEqual(row["page_end"], 4)
        self.assertEqual(row["unit_kind"], "pdf_paragraph")
        self.assertEqual(row["quality_status"], "usable")

    def test_null_visual_page_refs_deserializes_to_empty_list(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(visual_page_refs_json=None),
            chunk=_make_chunk(),
        )
        self.assertEqual(row["visual_page_refs"], [])

    def test_empty_document_class_normalizes_to_none(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(document_class="  "),
            chunk=_make_chunk(),
        )
        self.assertIsNone(row["document_class"])

    def test_diagnostics_ref_prefers_linkage_over_document(self):
        row = _serialize_index_row(
            linkage=_make_linkage(diagnostics_ref="linkage_diag"),
            document=_make_document(diagnostics_ref="doc_diag"),
            chunk=_make_chunk(),
        )
        self.assertEqual(row["diagnostics_ref"], "linkage_diag")

    def test_diagnostics_ref_does_not_fall_back_to_document(self):
        row = _serialize_index_row(
            linkage=_make_linkage(diagnostics_ref=None),
            document=_make_document(diagnostics_ref="doc_diag"),
            chunk=_make_chunk(),
        )
        self.assertIsNone(row["diagnostics_ref"])

    def test_null_page_start_serializes_as_none(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(),
            chunk=_make_chunk(page_start=None, page_end=None),
        )
        self.assertIsNone(row["page_start"])
        self.assertIsNone(row["page_end"])


# ---------------------------------------------------------------------------
# 2. _index_signature tests
# ---------------------------------------------------------------------------

class TestIndexSignature(unittest.TestCase):
    """Verify that _index_signature includes visual_page_refs and
    diagnostics_ref so bundle checksums change when these fields change."""

    def test_visual_page_refs_in_signature(self):
        row = _make_serialized_row()
        sig = _index_signature(row)
        self.assertIn("visual_page_refs", sig)
        self.assertEqual(len(sig["visual_page_refs"]), 1)

    def test_diagnostics_ref_in_signature(self):
        row = _make_serialized_row()
        sig = _index_signature(row)
        self.assertIn("diagnostics_ref", sig)
        self.assertIsNotNone(sig["diagnostics_ref"])

    def test_signature_changes_when_visual_refs_change(self):
        row_a = _make_serialized_row()
        row_b = _make_serialized_row(visual_page_refs=[])
        sig_a = json.dumps(_index_signature(row_a), sort_keys=True)
        sig_b = json.dumps(_index_signature(row_b), sort_keys=True)
        self.assertNotEqual(sig_a, sig_b)

    def test_signature_changes_when_diagnostics_ref_changes(self):
        row_a = _make_serialized_row(diagnostics_ref="ref_a")
        row_b = _make_serialized_row(diagnostics_ref="ref_b")
        sig_a = json.dumps(_index_signature(row_a), sort_keys=True)
        sig_b = json.dumps(_index_signature(row_b), sort_keys=True)
        self.assertNotEqual(sig_a, sig_b)


# ---------------------------------------------------------------------------
# 3. grouped_page tests
# ---------------------------------------------------------------------------

class TestGroupedPage(unittest.TestCase):
    """Verify that grouped_page() propagates document-level fields from
    the serialized item into the group dict."""

    def _make_item(self, **overrides: Any) -> dict[str, Any]:
        base = _make_serialized_row()
        base["group_id"] = contract.group_id_for_item(base)
        # Add fields that grouped_page reads via item.get()
        base["matched_unique_query_terms"] = 0
        base["summed_term_frequency"] = 0
        base["snippet_text"] = base["chunk_text"]
        base["snippet_start_char"] = 0
        base["snippet_end_char"] = len(base["chunk_text"])
        base["highlight_spans"] = []
        base.update(overrides)
        return base

    def test_group_has_visual_page_refs(self):
        items = [self._make_item()]
        groups = contract.grouped_page(items, mode="browse")
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["visual_page_refs"]), 1)
        self.assertEqual(
            groups[0]["visual_page_refs"][0]["visual_artifact_dpi"], 200
        )

    def test_group_has_document_class_and_media_type(self):
        items = [self._make_item()]
        groups = contract.grouped_page(items, mode="browse")
        self.assertEqual(groups[0]["document_class"], "inspection_report")
        self.assertEqual(groups[0]["media_type"], "application/pdf")

    def test_group_has_page_count(self):
        items = [self._make_item()]
        groups = contract.grouped_page(items, mode="browse")
        self.assertEqual(groups[0]["page_count"], 12)

    def test_group_has_blob_ref_and_sha256(self):
        items = [self._make_item()]
        groups = contract.grouped_page(items, mode="browse")
        self.assertIsNotNone(groups[0]["blob_ref"])
        self.assertIsNotNone(groups[0]["blob_sha256"])

    def test_group_has_diagnostics_ref(self):
        items = [self._make_item()]
        groups = contract.grouped_page(items, mode="browse")
        self.assertIsNotNone(groups[0]["diagnostics_ref"])

    def test_group_has_normalized_text_ref(self):
        items = [self._make_item()]
        groups = contract.grouped_page(items, mode="browse")
        self.assertIsNotNone(groups[0]["normalized_text_ref"])
        self.assertIsNotNone(groups[0]["normalized_text_sha256"])

    def test_multiple_chunks_share_document_fields(self):
        """Two chunks with the same group key produce one group
        that carries document-level fields from the first chunk."""
        item_a = self._make_item(chunk_id="chunk-001", chunk_ordinal=0)
        item_b = self._make_item(chunk_id="chunk-002", chunk_ordinal=1)
        groups = contract.grouped_page([item_a, item_b], mode="browse")
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["chunk_count"], 2)
        self.assertEqual(groups[0]["document_class"], "inspection_report")


# ---------------------------------------------------------------------------
# 4. Pydantic schema tests
# ---------------------------------------------------------------------------

class TestEvidenceChunkSchema(unittest.TestCase):
    """Verify NrcApsEvidenceChunkOut accepts chunk-level provenance fields."""

    def _make_chunk_data(self, **overrides: Any) -> dict[str, Any]:
        data = {
            "content_id": "cid-001",
            "chunk_id": "chunk-001",
            "group_id": "grp-001",
            "content_contract_id": "aps_content_v1",
            "chunking_contract_id": "aps_chunking_v1",
            "normalization_contract_id": "aps_norm_v1",
            "chunk_ordinal": 0,
            "start_char": 0,
            "end_char": 500,
            "chunk_text": "sample text",
            "chunk_text_sha256": "aa" * 32,
            "snippet_text": "sample text",
            "snippet_start_char": 0,
            "snippet_end_char": 11,
            "run_id": "run-001",
            "target_id": "tgt-001",
        }
        data.update(overrides)
        return data

    def test_chunk_accepts_page_start_and_end(self):
        out = NrcApsEvidenceChunkOut(**self._make_chunk_data(
            page_start=3, page_end=4
        ))
        self.assertEqual(out.page_start, 3)
        self.assertEqual(out.page_end, 4)

    def test_chunk_accepts_unit_kind(self):
        out = NrcApsEvidenceChunkOut(**self._make_chunk_data(
            unit_kind="pdf_paragraph"
        ))
        self.assertEqual(out.unit_kind, "pdf_paragraph")

    def test_chunk_accepts_quality_status(self):
        out = NrcApsEvidenceChunkOut(**self._make_chunk_data(
            quality_status="usable"
        ))
        self.assertEqual(out.quality_status, "usable")

    def test_chunk_accepts_diagnostics_ref(self):
        out = NrcApsEvidenceChunkOut(**self._make_chunk_data(
            diagnostics_ref="nrc_adams_aps/diagnostics/sha256/ab/cd/abcd.json"
        ))
        self.assertIsNotNone(out.diagnostics_ref)

    def test_chunk_fields_default_to_none(self):
        out = NrcApsEvidenceChunkOut(**self._make_chunk_data())
        self.assertIsNone(out.page_start)
        self.assertIsNone(out.page_end)
        self.assertIsNone(out.unit_kind)
        self.assertIsNone(out.quality_status)
        self.assertIsNone(out.diagnostics_ref)


class TestEvidenceGroupSchema(unittest.TestCase):
    """Verify NrcApsEvidenceGroupOut accepts document-level provenance fields."""

    def _make_group_data(self, **overrides: Any) -> dict[str, Any]:
        data = {
            "group_id": "grp-001",
            "content_id": "cid-001",
            "run_id": "run-001",
            "target_id": "tgt-001",
            "content_contract_id": "aps_content_v1",
            "chunking_contract_id": "aps_chunking_v1",
            "chunk_count": 1,
        }
        data.update(overrides)
        return data

    def test_group_accepts_visual_page_refs(self):
        vpr = [{
            "page_number": 1,
            "visual_page_class": "diagram_or_visual",
            "status": "preserved",
            "visual_artifact_ref": "nrc_adams_aps/visual_pages/sha256/ab/cd/test.png",
            "visual_artifact_sha256": "abcd" + "0" * 60,
            "visual_artifact_dpi": 200,
            "visual_artifact_format": "png",
            "visual_artifact_semantics": "whole_page_rasterization",
        }]
        out = NrcApsEvidenceGroupOut(**self._make_group_data(
            visual_page_refs=vpr
        ))
        self.assertEqual(len(out.visual_page_refs), 1)
        self.assertEqual(out.visual_page_refs[0]["visual_artifact_dpi"], 200)

    def test_group_accepts_document_class_and_media_type(self):
        out = NrcApsEvidenceGroupOut(**self._make_group_data(
            document_class="inspection_report",
            media_type="application/pdf",
        ))
        self.assertEqual(out.document_class, "inspection_report")
        self.assertEqual(out.media_type, "application/pdf")

    def test_group_accepts_page_count(self):
        out = NrcApsEvidenceGroupOut(**self._make_group_data(page_count=12))
        self.assertEqual(out.page_count, 12)

    def test_group_accepts_blob_ref_and_sha256(self):
        out = NrcApsEvidenceGroupOut(**self._make_group_data(
            blob_ref="nrc_adams_aps/blobs/sha256/12/34/1234.pdf",
            blob_sha256="1234" + "0" * 60,
        ))
        self.assertIsNotNone(out.blob_ref)
        self.assertIsNotNone(out.blob_sha256)

    def test_group_accepts_diagnostics_ref(self):
        out = NrcApsEvidenceGroupOut(**self._make_group_data(
            diagnostics_ref="nrc_adams_aps/diagnostics/sha256/ab/cd/abcd.json"
        ))
        self.assertIsNotNone(out.diagnostics_ref)

    def test_group_accepts_normalized_text_fields(self):
        out = NrcApsEvidenceGroupOut(**self._make_group_data(
            normalized_text_ref="nrc_adams_aps/normalized/sha256/ef/01/ef01.txt",
            normalized_text_sha256="ef01" + "0" * 60,
        ))
        self.assertIsNotNone(out.normalized_text_ref)
        self.assertIsNotNone(out.normalized_text_sha256)

    def test_group_defaults_empty_visual_page_refs(self):
        out = NrcApsEvidenceGroupOut(**self._make_group_data())
        self.assertEqual(out.visual_page_refs, [])
        self.assertEqual(out.page_count, 0)
        self.assertIsNone(out.document_class)
        self.assertIsNone(out.media_type)
        self.assertIsNone(out.diagnostics_ref)
        self.assertIsNone(out.blob_ref)
        self.assertIsNone(out.blob_sha256)
        self.assertIsNone(out.normalized_text_ref)
        self.assertIsNone(out.normalized_text_sha256)


# ---------------------------------------------------------------------------
# 5. End-to-end roundtrip: serialize -> group -> schema validation
# ---------------------------------------------------------------------------

class TestEndToEndRoundtrip(unittest.TestCase):
    """Full roundtrip: ORM mock -> _serialize_index_row -> grouped_page ->
    Pydantic validation. Proves no fields are silently dropped."""

    def test_full_provenance_roundtrip(self):
        # Step 1: Serialize from ORM mocks
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(),
            chunk=_make_chunk(),
        )
        row["group_id"] = contract.group_id_for_item(row)
        row["matched_unique_query_terms"] = 0
        row["summed_term_frequency"] = 0
        row["snippet_text"] = row["chunk_text"]
        row["snippet_start_char"] = 0
        row["snippet_end_char"] = len(row["chunk_text"])
        row["highlight_spans"] = []

        # Step 2: Group assembly
        groups = contract.grouped_page([row], mode="browse")
        self.assertEqual(len(groups), 1)
        group = groups[0]

        # Step 3: Validate group schema
        group_out = NrcApsEvidenceGroupOut(**group)
        self.assertEqual(group_out.document_class, "inspection_report")
        self.assertEqual(group_out.media_type, "application/pdf")
        self.assertEqual(group_out.page_count, 12)
        self.assertEqual(len(group_out.visual_page_refs), 1)
        self.assertIsNotNone(group_out.blob_ref)
        self.assertIsNotNone(group_out.diagnostics_ref)

        # Step 4: Validate chunk schema
        chunk_data = group["chunks"][0]
        chunk_out = NrcApsEvidenceChunkOut(**chunk_data)
        self.assertEqual(chunk_out.page_start, 3)
        self.assertEqual(chunk_out.page_end, 4)
        self.assertEqual(chunk_out.unit_kind, "pdf_paragraph")
        self.assertEqual(chunk_out.quality_status, "usable")

    def test_visual_artifact_fields_survive_roundtrip(self):
        """Artifact-specific fields within visual_page_refs survive the
        full serialization -> group -> schema pipeline."""
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(),
            chunk=_make_chunk(),
        )
        row["group_id"] = contract.group_id_for_item(row)
        row["matched_unique_query_terms"] = 0
        row["summed_term_frequency"] = 0
        row["snippet_text"] = row["chunk_text"]
        row["snippet_start_char"] = 0
        row["snippet_end_char"] = len(row["chunk_text"])
        row["highlight_spans"] = []

        groups = contract.grouped_page([row], mode="browse")
        group_out = NrcApsEvidenceGroupOut(**groups[0])
        vpr = group_out.visual_page_refs[0]

        self.assertEqual(vpr["visual_artifact_ref"],
                         "nrc_adams_aps/visual_pages/sha256/ab/cd/specimen.png")
        self.assertEqual(vpr["visual_artifact_sha256"], "abcd" + "0" * 60)
        self.assertEqual(vpr["visual_artifact_dpi"], 200)
        self.assertEqual(vpr["visual_artifact_format"], "png")
        self.assertEqual(vpr["visual_artifact_semantics"], "whole_page_rasterization")


# ---------------------------------------------------------------------------
# 6. Provenance hardening: diagnostics_ref resolver + quality_status fallback
# ---------------------------------------------------------------------------

class TestResolveDiagnosticsRef(unittest.TestCase):
    """Verify _resolve_diagnostics_ref returns linkage-only value.

    Diagnostics artifacts are run-target-specific.  The deduplicated
    document row must NOT be used as a fallback (authority:
    nrc_aps_status_handoff.md Section 3 Content indexing).
    """

    def test_linkage_wins_when_both_present(self):
        from app.services.nrc_aps_content_index import _resolve_diagnostics_ref
        linkage = _make_linkage(diagnostics_ref="linkage_diag")
        document = _make_document(diagnostics_ref="doc_diag")
        self.assertEqual(_resolve_diagnostics_ref(linkage, document), "linkage_diag")

    def test_no_document_fallback_when_linkage_absent(self):
        from app.services.nrc_aps_content_index import _resolve_diagnostics_ref
        linkage = _make_linkage(diagnostics_ref=None)
        document = _make_document(diagnostics_ref="doc_diag")
        self.assertIsNone(_resolve_diagnostics_ref(linkage, document))

    def test_none_when_both_absent(self):
        from app.services.nrc_aps_content_index import _resolve_diagnostics_ref
        linkage = _make_linkage(diagnostics_ref=None)
        document = _make_document(diagnostics_ref=None)
        self.assertIsNone(_resolve_diagnostics_ref(linkage, document))

    def test_whitespace_only_treated_as_absent(self):
        from app.services.nrc_aps_content_index import _resolve_diagnostics_ref
        linkage = _make_linkage(diagnostics_ref="   ")
        document = _make_document(diagnostics_ref="doc_diag")
        self.assertIsNone(_resolve_diagnostics_ref(linkage, document))


class TestContentIndexSerializerDiagnosticsRef(unittest.TestCase):
    """Verify the content-index _serialize_index_row uses linkage-only resolver."""

    def test_linkage_value_used_when_present(self):
        from app.services.nrc_aps_content_index import _serialize_index_row as ci_serialize
        row = ci_serialize(
            linkage=_make_linkage(diagnostics_ref="linkage_val"),
            document=_make_document(diagnostics_ref="doc_val"),
            chunk=_make_chunk(),
        )
        self.assertEqual(row["diagnostics_ref"], "linkage_val")

    def test_no_document_fallback_when_linkage_absent(self):
        from app.services.nrc_aps_content_index import _serialize_index_row as ci_serialize
        row = ci_serialize(
            linkage=_make_linkage(diagnostics_ref=None),
            document=_make_document(diagnostics_ref="doc_val"),
            chunk=_make_chunk(),
        )
        self.assertIsNone(row["diagnostics_ref"])


class TestEvidenceBundleSerializerDiagnosticsRef(unittest.TestCase):
    """Verify the evidence-bundle _serialize_index_row uses linkage-only resolver."""

    def test_linkage_value_used_when_present(self):
        row = _serialize_index_row(
            linkage=_make_linkage(diagnostics_ref="linkage_val"),
            document=_make_document(diagnostics_ref="doc_val"),
            chunk=_make_chunk(),
        )
        self.assertEqual(row["diagnostics_ref"], "linkage_val")

    def test_no_document_fallback_when_linkage_absent(self):
        row = _serialize_index_row(
            linkage=_make_linkage(diagnostics_ref=None),
            document=_make_document(diagnostics_ref="doc_val"),
            chunk=_make_chunk(),
        )
        self.assertIsNone(row["diagnostics_ref"])


class TestEvidenceBundleQualityStatusFallback(unittest.TestCase):
    """Verify evidence-bundle serializer falls back to document.quality_status
    when chunk.quality_status is absent."""

    def test_chunk_quality_used_when_present(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(quality_status="weak"),
            chunk=_make_chunk(quality_status="usable"),
        )
        self.assertEqual(row["quality_status"], "usable")

    def test_document_fallback_when_chunk_absent(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(quality_status="weak"),
            chunk=_make_chunk(quality_status=None),
        )
        self.assertEqual(row["quality_status"], "weak")

    def test_none_when_both_absent(self):
        row = _serialize_index_row(
            linkage=_make_linkage(),
            document=_make_document(quality_status=None),
            chunk=_make_chunk(quality_status=None),
        )
        self.assertIsNone(row["quality_status"])


if __name__ == "__main__":
    unittest.main()


