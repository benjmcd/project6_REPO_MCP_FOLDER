import unittest
from unittest.mock import MagicMock, patch, ANY, PropertyMock
import hashlib
import json
import sys
import os
import tempfile

# Mock heavy dependencies at the system level before any server-side imports
mock_camelot = MagicMock()
sys.modules['camelot'] = mock_camelot
mock_paddle = MagicMock()
sys.modules['paddleocr'] = mock_paddle
mock_np = MagicMock()
sys.modules['numpy'] = mock_np

# Now import the services under test
from app.services import nrc_aps_advanced_table_parser
from app.services import nrc_aps_advanced_ocr
from app.services import nrc_aps_document_processing
from app.services import nrc_aps_content_index
from app.services import nrc_aps_ocr as _real_nrc_aps_ocr
from app.services import nrc_aps_settings
import fitz

class TestAdvancedAdapters(unittest.TestCase):

    @patch('app.services.nrc_aps_advanced_table_parser.camelot')
    def test_table_adapter_multiple_tables(self, patched_camelot):
        """Verify multiple tables per page, single-pass Camelot, and hull-based geometry."""
        # Setup fitz mock for page height
        with patch('fitz.open') as mock_fitz_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.rect.height = 1000
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__enter__.return_value = mock_doc
            mock_fitz_open.return_value = mock_doc

            # Mock two Camelot tables
            mock_tab1 = MagicMock()
            mock_tab2 = MagicMock()

            # Setup cells for tab1: (10, 10, 50, 50) bottom-left
            c1 = MagicMock(); c1.x1, c1.y1, c1.x2, c1.y2 = 10, 10, 50, 50
            mock_tab1.cells = [[c1]]
            mock_tab1.df = MagicMock()
            mock_tab1.df.iterrows.return_value = []

            # Setup cells for tab2: (60, 60, 100, 100) bottom-left
            c2 = MagicMock(); c2.x1, c2.y1, c2.x2, c2.y2 = 60, 60, 100, 100
            mock_tab2.cells = [[c2]]
            mock_tab2.df = MagicMock()
            mock_tab2.df.iterrows.return_value = []

            # GOAL 3: Ensure _bbox is NOT accessed
            type(mock_tab1)._bbox = PropertyMock(side_effect=AttributeError("Should not access _bbox"))
            type(mock_tab2)._bbox = PropertyMock(side_effect=AttributeError("Should not access _bbox"))

            # GOAL 2: camelot.read_pdf returned 2 tables
            patched_camelot.read_pdf.return_value = [mock_tab1, mock_tab2]

            result = nrc_aps_advanced_table_parser.extract_advanced_table(
                pdf_source=b"%PDF-bytes",
                page_index_0=0
            )

            # Assertions
            self.assertEqual(len(result['tables']), 2)
            self.assertEqual(len(result['exclusion_bboxes']), 2)
            self.assertEqual(patched_camelot.read_pdf.call_count, 1)  # SINGLE CALL

            # Assert bboxes (Top-left mapping: y_top = height - c_y_top)
            self.assertEqual(result['exclusion_bboxes'][0], [10.0, 950.0, 50.0, 990.0])
            self.assertEqual(result['exclusion_bboxes'][1], [60.0, 900.0, 100.0, 940.0])

    def test_ocr_adapter_confidence_scaling(self):
        """Verify 0-1.0 confidence is scaled to 0-100.0."""
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.samples = b'\x00' * (100 * 100 * 3)
        mock_pix.height = 100
        mock_pix.width = 100
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [ [ [ [[0,0], [1,0], [1,1], [0,1]], ("test", 0.85) ] ] ]
        
        with patch('app.services.nrc_aps_advanced_ocr._get_paddle_instance', return_value=mock_engine):
            result = nrc_aps_advanced_ocr.run_advanced_ocr(mock_page)
            self.assertAlmostEqual(result['average_confidence'], 85.0)

    def test_ocr_adapter_weights_missing_scoped_patch(self):
        """GOAL 4: Verify weights-missing logic using module-scoped patch."""
        with patch('app.services.nrc_aps_advanced_ocr.os.path.exists', return_value=False):
            with self.assertRaises(FileNotFoundError):
                nrc_aps_advanced_ocr.run_advanced_ocr(MagicMock())

class TestProcessorSignals(unittest.TestCase):
    """GOAL 1: Exercise the REAL reachable processor path for signaling verification."""

    @patch('app.services.nrc_aps_document_processing._extract_native_pdf_units')
    @patch('app.services.nrc_aps_document_processing._quality_metrics')
    @patch('app.services.nrc_aps_document_processing._degradation_codes_for_detection')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_ocr')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_advanced_ocr')
    @patch('fitz.open')
    def test_processor_ocr_failure_signaling_real_path(self, mock_fitz_open, mock_adv_ocr, mock_ocr, mock_deg, mock_quality, mock_native):
        # Setup fitz mock
        mock_doc = MagicMock(spec=fitz.Document)
        mock_doc.page_count = 1
        mock_doc.needs_pass = False 
        
        mock_page = MagicMock(spec=fitz.Page)
        mock_page.number = 0
        mock_page.rect.width = 100
        mock_page.rect.height = 100
        mock_doc.load_page.return_value = mock_page
        mock_fitz_open.return_value = mock_doc
        
        # Setup quality to trigger OCR routing
        mock_native.return_value = []
        # Return all keys expected by _process_pdf page summarization loop
        mock_quality.return_value = {
            "quality_status": "weak", 
            "char_count": 0,
            "token_count": 0,
            "quality_metrics": {}
        }
        mock_deg.return_value = []
        mock_ocr.OcrExecutionError = _real_nrc_aps_ocr.OcrExecutionError
        mock_ocr.tesseract_available.return_value = False

        config = nrc_aps_document_processing.default_processing_config({
            "document_type": "AdvancedDoc",
            "ocr_enabled": True
        })
        
        # Sub-test 1: FileNotFoundError -> advanced_ocr_weights_missing
        mock_adv_ocr.run_advanced_ocr.side_effect = FileNotFoundError()
        result = nrc_aps_document_processing._process_pdf(
            content=b"%PDF",
            detection={"effective_content_type": "application/pdf"},
            config=config,
            deadline=None
        )
        self.assertIn("advanced_ocr_weights_missing", result["degradation_codes"])
        
        # Sub-test 2: RuntimeError -> advanced_ocr_execution_failed
        mock_adv_ocr.run_advanced_ocr.side_effect = RuntimeError("Engine crash")
        result = nrc_aps_document_processing._process_pdf(
            content=b"%PDF",
            detection={"effective_content_type": "application/pdf"},
            config=config,
            deadline=None
        )
        self.assertIn("advanced_ocr_execution_failed", result["degradation_codes"])

class TestVisualPageArtifact(unittest.TestCase):
    """Tests for _write_visual_page_artifact and the visual-preservation
    artifact materialization integration."""

    def test_write_visual_page_artifact_stores_png_content_addressed(self):
        """_write_visual_page_artifact renders a page to PNG, stores it
        content-addressed, and returns the correct metadata dict."""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal bytes
        expected_sha = hashlib.sha256(fake_png).hexdigest()

        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = fake_png

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap

        with tempfile.TemporaryDirectory() as tmpdir:
            result = nrc_aps_document_processing._write_visual_page_artifact(
                artifact_storage_dir=tmpdir,
                page=mock_page,
                page_number=3,
                config={"visual_render_dpi": 200},
            )

            # Verify returned metadata fields
            self.assertEqual(result["visual_artifact_sha256"], expected_sha)
            self.assertEqual(result["visual_artifact_dpi"], 200)
            self.assertEqual(result["visual_artifact_format"], "png")
            self.assertEqual(result["visual_artifact_semantics"], "whole_page_rasterization")

            # visual_artifact_ref must be storage-relative, not absolute
            ref = result["visual_artifact_ref"]
            self.assertTrue(ref.startswith("nrc_adams_aps/visual_pages/sha256/"))
            self.assertFalse(os.path.isabs(ref))
            self.assertTrue(ref.endswith(f"{expected_sha}.png"))

            # The PNG must exist on disk and match the sha256
            from pathlib import Path
            stored_file = Path(tmpdir) / ref
            self.assertTrue(stored_file.exists())
            self.assertEqual(hashlib.sha256(stored_file.read_bytes()).hexdigest(), expected_sha)

            # Rendering was called at the requested DPI
            mock_page.get_pixmap.assert_called_once_with(dpi=200)

    def test_write_visual_page_artifact_idempotent(self):
        """Writing the same content twice must not fail (content-addressed)."""
        fake_png = b"\x89PNGidempotent"
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = fake_png
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap

        with tempfile.TemporaryDirectory() as tmpdir:
            r1 = nrc_aps_document_processing._write_visual_page_artifact(
                artifact_storage_dir=tmpdir, page=mock_page, page_number=1,
                config={"visual_render_dpi": 150},
            )
            r2 = nrc_aps_document_processing._write_visual_page_artifact(
                artifact_storage_dir=tmpdir, page=mock_page, page_number=1,
                config={"visual_render_dpi": 150},
            )
            self.assertEqual(r1, r2)

    def test_write_visual_page_artifact_default_dpi(self):
        """When visual_render_dpi is not in config, default DPI is used."""
        fake_png = b"\x89PNGdefault"
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = fake_png
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap

        with tempfile.TemporaryDirectory() as tmpdir:
            result = nrc_aps_document_processing._write_visual_page_artifact(
                artifact_storage_dir=tmpdir, page=mock_page, page_number=1,
                config={},
            )
            self.assertEqual(
                result["visual_artifact_dpi"],
                nrc_aps_document_processing.APS_VISUAL_RENDER_DPI_DEFAULT,
            )
            mock_page.get_pixmap.assert_called_once_with(
                dpi=nrc_aps_document_processing.APS_VISUAL_RENDER_DPI_DEFAULT,
            )


class TestVisualArtifactIntegration(unittest.TestCase):
    """Integration tests proving artifact fields propagate through the
    visual-preservation lane in _process_pdf."""

    @patch('app.services.nrc_aps_document_processing._extract_native_pdf_units')
    @patch('app.services.nrc_aps_document_processing._quality_metrics')
    @patch('app.services.nrc_aps_document_processing._degradation_codes_for_detection')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_ocr')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_advanced_ocr')
    @patch('fitz.open')
    def test_preserve_eligible_page_produces_artifact_fields(
        self, mock_fitz_open, mock_adv_ocr, mock_ocr, mock_deg, mock_quality, mock_native
    ):
        """When artifact_storage_dir is configured, preserve-eligible pages
        produce visual_page_ref dicts containing all artifact fields."""
        mock_doc = MagicMock(spec=fitz.Document)
        mock_doc.page_count = 1
        mock_doc.needs_pass = False
        mock_page = MagicMock(spec=fitz.Page)
        mock_page.number = 0
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0
        mock_doc.load_page.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        # Make the page classify as visual (weak quality + has visual content)
        mock_native.return_value = []
        mock_quality.return_value = {
            "quality_status": "weak",
            "char_count": 0,
            "token_count": 0,
            "quality_metrics": {},
        }
        mock_deg.return_value = []
        mock_ocr.OcrExecutionError = _real_nrc_aps_ocr.OcrExecutionError
        mock_ocr.tesseract_available.return_value = False
        mock_adv_ocr.run_advanced_ocr.side_effect = FileNotFoundError()

        # Mock _has_significant_visual_content to return True
        with patch.object(
            nrc_aps_document_processing, '_has_significant_visual_content', return_value=True
        ):
            fake_png = b"\x89PNG_artifact_test"
            expected_sha = hashlib.sha256(fake_png).hexdigest()
            mock_pixmap = MagicMock()
            mock_pixmap.tobytes.return_value = fake_png
            mock_page.get_pixmap.return_value = mock_pixmap

            with tempfile.TemporaryDirectory() as tmpdir:
                config = nrc_aps_document_processing.default_processing_config({
                    "artifact_storage_dir": tmpdir,
                    "visual_render_dpi": 200,
                    "ocr_enabled": True,
                })
                result = nrc_aps_document_processing._process_pdf(
                    content=b"%PDF",
                    detection={"effective_content_type": "application/pdf"},
                    config=config,
                    deadline=None,
                )

                self.assertTrue(len(result["visual_page_refs"]) >= 1)
                vpr = result["visual_page_refs"][0]

                # Existing fields preserved
                self.assertEqual(vpr["page_number"], 1)
                self.assertEqual(vpr["visual_page_class"], "diagram_or_visual")
                self.assertEqual(vpr["status"], "preserved")
                self.assertEqual(vpr["width"], 612.0)
                self.assertEqual(vpr["height"], 792.0)

                # New artifact fields present
                self.assertEqual(vpr["visual_artifact_sha256"], expected_sha)
                self.assertEqual(vpr["visual_artifact_dpi"], 200)
                self.assertEqual(vpr["visual_artifact_format"], "png")
                self.assertEqual(vpr["visual_artifact_semantics"], "whole_page_rasterization")
                self.assertTrue(vpr["visual_artifact_ref"].startswith("nrc_adams_aps/visual_pages/sha256/"))
                self.assertFalse(os.path.isabs(vpr["visual_artifact_ref"]))

    @patch('app.services.nrc_aps_document_processing._extract_native_pdf_units')
    @patch('app.services.nrc_aps_document_processing._quality_metrics')
    @patch('app.services.nrc_aps_document_processing._degradation_codes_for_detection')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_ocr')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_advanced_ocr')
    @patch('fitz.open')
    def test_artifact_failure_degrades_gracefully(
        self, mock_fitz_open, mock_adv_ocr, mock_ocr, mock_deg, mock_quality, mock_native
    ):
        """When artifact rendering fails, the ref is still appended with
        status='visual_capture_failed' and no artifact fields."""
        mock_doc = MagicMock(spec=fitz.Document)
        mock_doc.page_count = 1
        mock_doc.needs_pass = False
        mock_page = MagicMock(spec=fitz.Page)
        mock_page.number = 0
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0
        mock_doc.load_page.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        mock_native.return_value = []
        mock_quality.return_value = {
            "quality_status": "weak",
            "char_count": 0,
            "token_count": 0,
            "quality_metrics": {},
        }
        mock_deg.return_value = []
        mock_ocr.OcrExecutionError = _real_nrc_aps_ocr.OcrExecutionError
        mock_ocr.tesseract_available.return_value = False
        mock_adv_ocr.run_advanced_ocr.side_effect = FileNotFoundError()

        with patch.object(
            nrc_aps_document_processing, '_has_significant_visual_content', return_value=True
        ):
            # Make get_pixmap blow up to simulate rendering failure
            mock_page.get_pixmap.side_effect = RuntimeError("rendering failed")

            with tempfile.TemporaryDirectory() as tmpdir:
                config = nrc_aps_document_processing.default_processing_config({
                    "artifact_storage_dir": tmpdir,
                    "ocr_enabled": True,
                })
                result = nrc_aps_document_processing._process_pdf(
                    content=b"%PDF",
                    detection={"effective_content_type": "application/pdf"},
                    config=config,
                    deadline=None,
                )

                self.assertTrue(len(result["visual_page_refs"]) >= 1)
                vpr = result["visual_page_refs"][0]

                # Provenance fields preserved
                self.assertEqual(vpr["page_number"], 1)
                self.assertEqual(vpr["visual_page_class"], "diagram_or_visual")
                self.assertEqual(vpr["status"], "visual_capture_failed")

                # No artifact fields
                self.assertNotIn("visual_artifact_ref", vpr)
                self.assertNotIn("visual_artifact_sha256", vpr)

                # Degradation code recorded
                self.assertIn("visual_artifact_failed", result["degradation_codes"])

    @patch('app.services.nrc_aps_document_processing._extract_native_pdf_units')
    @patch('app.services.nrc_aps_document_processing._quality_metrics')
    @patch('app.services.nrc_aps_document_processing._degradation_codes_for_detection')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_ocr')
    @patch('app.services.nrc_aps_document_processing.nrc_aps_advanced_ocr')
    @patch('fitz.open')
    def test_no_artifact_storage_dir_skips_materialization(
        self, mock_fitz_open, mock_adv_ocr, mock_ocr, mock_deg, mock_quality, mock_native
    ):
        """When artifact_storage_dir is not configured, visual_page_refs are
        metadata-only (no artifact fields) — backward compatible."""
        mock_doc = MagicMock(spec=fitz.Document)
        mock_doc.page_count = 1
        mock_doc.needs_pass = False
        mock_page = MagicMock(spec=fitz.Page)
        mock_page.number = 0
        mock_page.rect.width = 612.0
        mock_page.rect.height = 792.0
        mock_doc.load_page.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        mock_native.return_value = []
        mock_quality.return_value = {
            "quality_status": "weak",
            "char_count": 0,
            "token_count": 0,
            "quality_metrics": {},
        }
        mock_deg.return_value = []
        mock_ocr.OcrExecutionError = _real_nrc_aps_ocr.OcrExecutionError
        mock_ocr.tesseract_available.return_value = False
        mock_adv_ocr.run_advanced_ocr.side_effect = FileNotFoundError()

        with patch.object(
            nrc_aps_document_processing, '_has_significant_visual_content', return_value=True
        ):
            config = nrc_aps_document_processing.default_processing_config({
                "ocr_enabled": True,
            })
            result = nrc_aps_document_processing._process_pdf(
                content=b"%PDF",
                detection={"effective_content_type": "application/pdf"},
                config=config,
                deadline=None,
            )

            self.assertTrue(len(result["visual_page_refs"]) >= 1)
            vpr = result["visual_page_refs"][0]

            # Metadata-only, no artifact fields
            self.assertEqual(vpr["status"], "preserved")
            self.assertNotIn("visual_artifact_ref", vpr)
            self.assertNotIn("visual_artifact_sha256", vpr)


class TestVisualArtifactRoundtrip(unittest.TestCase):
    """Response-surface roundtrip proof: artifact fields must survive
    payload → DB serialization → deserialization → API response shape."""

    def test_visual_page_refs_roundtrips_through_search_response_surface(self):
        """Prove that new artifact-related fields in visual_page_refs roundtrip
        through JSON serialization (DB persist) → deserialization (DB read) →
        API response model validation without loss or error."""
        specimen = [
            {
                "page_number": 3,
                "visual_page_class": "diagram_or_visual",
                "status": "preserved",
                "width": 612.0,
                "height": 792.0,
                "visual_artifact_ref": "nrc_adams_aps/visual_pages/sha256/ab/cd/abcdef1234567890.png",
                "visual_artifact_sha256": "abcdef1234567890" + "0" * 48,
                "visual_artifact_dpi": 200,
                "visual_artifact_format": "png",
                "visual_artifact_semantics": "whole_page_rasterization",
            }
        ]

        # Step 1: JSON serialization (simulates DB persist at content_index.py:649-650)
        serialized_json = json.dumps(specimen)

        # Step 2: Deserialization (simulates _deserialize_visual_page_refs)
        deserialized = nrc_aps_content_index._deserialize_visual_page_refs(serialized_json)

        # All fields survive roundtrip
        self.assertEqual(len(deserialized), 1)
        rt = deserialized[0]
        self.assertEqual(rt["page_number"], 3)
        self.assertEqual(rt["visual_page_class"], "diagram_or_visual")
        self.assertEqual(rt["status"], "preserved")
        self.assertEqual(rt["width"], 612.0)
        self.assertEqual(rt["height"], 792.0)
        self.assertEqual(rt["visual_artifact_ref"], specimen[0]["visual_artifact_ref"])
        self.assertEqual(rt["visual_artifact_sha256"], specimen[0]["visual_artifact_sha256"])
        self.assertEqual(rt["visual_artifact_dpi"], 200)
        self.assertEqual(rt["visual_artifact_format"], "png")
        self.assertEqual(rt["visual_artifact_semantics"], "whole_page_rasterization")

        # Step 3: API response model validation (simulates Pydantic serialization)
        from app.schemas.api import ConnectorRunContentUnitOut
        model_data = {
            "content_id": "test-cid",
            "chunk_id": "test-chunk",
            "content_contract_id": "test-cc",
            "chunking_contract_id": "test-chk",
            "chunk_ordinal": 0,
            "start_char": 0,
            "end_char": 100,
            "chunk_text": "test",
            "chunk_text_sha256": "abc123",
            "run_id": "test-run",
            "target_id": "test-target",
            "blob_ref": "/path/to/source.pdf",
            "visual_page_refs": deserialized,
        }
        out = ConnectorRunContentUnitOut(**model_data)

        # Artifact fields survive Pydantic validation
        api_vpr = out.visual_page_refs
        self.assertEqual(len(api_vpr), 1)
        self.assertEqual(api_vpr[0]["visual_artifact_ref"], specimen[0]["visual_artifact_ref"])
        self.assertEqual(api_vpr[0]["visual_artifact_sha256"], specimen[0]["visual_artifact_sha256"])
        self.assertEqual(api_vpr[0]["visual_artifact_dpi"], 200)
        self.assertEqual(api_vpr[0]["visual_artifact_format"], "png")
        self.assertEqual(api_vpr[0]["visual_artifact_semantics"], "whole_page_rasterization")

        # blob_ref coexists (dual recovery contract)
        self.assertEqual(out.blob_ref, "/path/to/source.pdf")

    def test_failed_artifact_roundtrips_without_artifact_fields(self):
        """A visual_page_ref with status=visual_capture_failed and no artifact
        fields must also roundtrip cleanly."""
        specimen = [
            {
                "page_number": 5,
                "visual_page_class": "diagram_or_visual",
                "status": "visual_capture_failed",
            }
        ]
        serialized_json = json.dumps(specimen)
        deserialized = nrc_aps_content_index._deserialize_visual_page_refs(serialized_json)
        self.assertEqual(len(deserialized), 1)
        self.assertEqual(deserialized[0]["status"], "visual_capture_failed")
        self.assertNotIn("visual_artifact_ref", deserialized[0])


if __name__ == '__main__':
    unittest.main()
