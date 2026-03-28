import unittest

from app.services import aps_retrieval_plane_contract as contract


def _sample_row(**overrides):
    row = {
        "retrieval_contract_id": contract.APS_RETRIEVAL_CONTRACT_ID,
        "run_id": "run-001",
        "target_id": "target-001",
        "content_id": "content-001",
        "chunk_id": "chunk-001",
        "content_contract_id": "aps_content_units_v2",
        "chunking_contract_id": "aps_chunking_v2",
        "normalization_contract_id": "aps_text_normalization_v2",
        "accession_number": "ML25001A001",
        "chunk_ordinal": 0,
        "start_char": 0,
        "end_char": 42,
        "page_start": 1,
        "page_end": 1,
        "chunk_text": "retrieval plane sample text",
        "chunk_text_sha256": "a" * 64,
        "search_text": "retrieval plane sample text",
        "content_status": "indexed",
        "quality_status": "strong",
        "document_class": "inspection_report",
        "media_type": "application/pdf",
        "page_count": 3,
        "content_units_ref": "content_units.json",
        "normalized_text_ref": "normalized.txt",
        "blob_ref": "blob.pdf",
        "download_exchange_ref": "download.json",
        "discovery_ref": "discovery.json",
        "selection_ref": "selection.json",
        "diagnostics_ref": "diagnostics.json",
        "visual_page_refs_json": '[{"page_number":1,"status":"preserved"}]',
    }
    row.update(overrides)
    return row


class TestApsRetrievalPlaneContract(unittest.TestCase):
    def test_retrieval_chunk_id_is_stable_for_same_identity(self):
        base = _sample_row()
        changed = _sample_row(search_text="different search text", chunk_text="different search text")
        self.assertEqual(contract.derive_retrieval_chunk_id(base), contract.derive_retrieval_chunk_id(changed))

    def test_source_signature_changes_when_material_field_changes(self):
        base = _sample_row()
        changed = _sample_row(diagnostics_ref="other-diagnostics.json")
        self.assertNotEqual(contract.compute_source_signature(base), contract.compute_source_signature(changed))

    def test_visual_page_refs_are_canonicalized(self):
        raw = '[{"status":"preserved","page_number":1}]'
        self.assertEqual(
            contract.canonicalize_visual_page_refs(raw),
            '[{"page_number":1,"status":"preserved"}]',
        )


if __name__ == "__main__":
    unittest.main()
