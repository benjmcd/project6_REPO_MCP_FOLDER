import unittest
from unittest.mock import MagicMock, patch, ANY, PropertyMock
import sys
import os

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
from app.services import nrc_aps_settings
import fitz

class TestAdvancedAdapters(unittest.TestCase):

    def test_table_adapter_multiple_tables(self):
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
            mock_camelot.read_pdf.return_value = [mock_tab1, mock_tab2]
            mock_camelot.read_pdf.reset_mock()
            
            result = nrc_aps_advanced_table_parser.extract_advanced_table(
                pdf_source=b"%PDF-bytes", 
                page_index_0=0
            )
            
            # Assertions
            self.assertEqual(len(result['tables']), 2)
            self.assertEqual(len(result['exclusion_bboxes']), 2)
            self.assertEqual(mock_camelot.read_pdf.call_count, 1) # SINGLE CALL
            
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

if __name__ == '__main__':
    unittest.main()
