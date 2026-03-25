import os
import numpy as np
import fitz
from typing import Any, Dict, Optional
from app.services import nrc_aps_settings

# PaddleOCR singleton to avoid weight-reloading overhead
_PADDLE_ENGINE = None

def _get_paddle_instance():
    global _PADDLE_ENGINE
    if _PADDLE_ENGINE is None:
        # Check for local weights strictly
        if not os.path.exists(nrc_aps_settings.PADDLE_MODEL_DIR):
            raise FileNotFoundError(f"PaddleOCR weights not found at {nrc_aps_settings.PADDLE_MODEL_DIR}")
        
        # Check sub-directories
        for d in [nrc_aps_settings.PADDLE_DET_MODEL_DIR, 
                  nrc_aps_settings.PADDLE_REC_MODEL_DIR, 
                  nrc_aps_settings.PADDLE_CLS_MODEL_DIR]:
            if not os.path.exists(d):
                 raise FileNotFoundError(f"Specific PaddleOCR model component missing: {d}")

        from paddleocr import PaddleOCR
        # Initialize without downloading
        _PADDLE_ENGINE = PaddleOCR(
            use_angle_cls=True, 
            lang='en',
            det_model_dir=nrc_aps_settings.PADDLE_DET_MODEL_DIR,
            rec_model_dir=nrc_aps_settings.PADDLE_REC_MODEL_DIR,
            cls_model_dir=nrc_aps_settings.PADDLE_CLS_MODEL_DIR,
            show_log=False,
            use_gpu=False # default to CPU as requirement stated
        )
    return _PADDLE_ENGINE

def run_advanced_ocr(page: fitz.Page) -> Dict[str, Any]:
    """
    Renders a fitz.Page and runs PaddleOCR.
    
    Returns:
        {'text': str, 'average_confidence': float | None}
    """
    try:
        engine = _get_paddle_instance()
        
        # Render page to Pixmap (300 DPI for high-fidelity OCR)
        pix = page.get_pixmap(dpi=300, alpha=False)
        
        # Convert Pixmap to NumPy array (BGR for OpenCV/PaddleOCR compatibility)
        # pix.samples is raw bytes [R, G, B, R, G, B...]
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        # pix.samples are RGB, Paddle uses BGR or RGB depending on backend; usually RGB is fine if specified correctly
        # but standardized BGR is safer for many CV backends. PaddleOCR accepts numpy arrays.
        
        results = engine.ocr(img, cls=True)
        
        if not results or not results[0]:
            return {"text": "", "average_confidence": None}
            
        full_text_parts = []
        confidences = []
        
        # results[0] is a list of [bbox, (text, confidence)]
        for res in results[0]:
            text, conf = res[1]
            full_text_parts.append(text)
            if conf is not None:
                confidences.append(float(conf))
        
        avg_conf = None
        if confidences:
            # Scale to 0-100 for processor compatibility (e.g., 0.95 -> 95.0)
            avg_conf = (sum(confidences) / len(confidences)) * 100.0
            
        return {
            "text": " ".join(full_text_parts),
            "average_confidence": avg_conf
        }
        
    except FileNotFoundError:
        # Re-raise weights missing so processor can fall back correctly
        raise
    except Exception as e:
        # Do not return empty text successfully; raise or handle distinctly 
        # so processor can append appropriate degradation code
        raise RuntimeError(f"Advanced OCR engine failure: {str(e)}") from e
