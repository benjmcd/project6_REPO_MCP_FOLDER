import os
from pathlib import Path

# Core Configuration for Advanced NRC ADAMS Ingestion

# Document Type Routing
COMPLEX_TABLE_DOC_TYPES = {
    "Decommissioning Funding Plan",
    "Technical Specification Amendment",
    "Financial Report",
    "Decommissioning Financial Assurance",
}

ADVANCED_OCR_DOC_TYPES = {
    "Differing Professional Opinion Case File",
    "Part 21 Correspondence",
    "Handwritten Field Note",
    "Faxed Memo",
}

# OCR Fallback Configuration
OCR_FALLBACK_WORD_THRESHOLD = 50

# PaddleOCR Local Paths (Strictly no runtime downloads)
# Expected directory structure:
# ~/.cache/nrc_ocr_models/whl/det/en/en_PP-OCRv3_det_infer
# ~/.cache/nrc_ocr_models/whl/rec/en/en_PP-OCRv3_rec_infer
# ~/.cache/nrc_ocr_models/whl/cls/ch_ppocr_mobile_v2.0_cls_infer
PADDLE_MODEL_DIR = os.path.expanduser("~/.cache/nrc_ocr_models")
PADDLE_DET_MODEL_DIR = os.path.join(PADDLE_MODEL_DIR, "whl/det/en/en_PP-OCRv3_det_infer")
PADDLE_REC_MODEL_DIR = os.path.join(PADDLE_MODEL_DIR, "whl/rec/en/en_PP-OCRv3_rec_infer")
PADDLE_CLS_MODEL_DIR = os.path.join(PADDLE_MODEL_DIR, "whl/cls/ch_ppocr_mobile_v2.0_cls_infer")
