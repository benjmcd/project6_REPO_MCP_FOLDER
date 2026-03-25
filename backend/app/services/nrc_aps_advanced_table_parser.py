import tempfile
import os
import warnings
from typing import Any, List, Dict, Tuple
import camelot
import fitz

def extract_advanced_table(
    pdf_source: str | bytes, 
    page_index_0: int
) -> Dict[str, Any]:
    """
    Extracts tables from a specific page using Camelot (Stream flavor).
    
    Returns:
        Dict containing:
            'tables': List of units with kind 'pdf_table'
            'exclusion_bboxes': List of [x0, y0, x1, y1] regions
    """
    result = {
        "tables": [],
        "exclusion_bboxes": []
    }
    
    # Camelot requires a filesystem path.
    temp_pdf_path = None
    if isinstance(pdf_source, bytes):
        fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, 'wb') as tmp:
            tmp.write(pdf_source)
        path_to_process = temp_pdf_path
    else:
        path_to_process = str(pdf_source)

    try:
        # authoritative page height using fitz to ensure stable coordinate mapping
        # We look this up once per page processing.
        try:
            with fitz.open(path_to_process) as doc:
                page_height = doc[page_index_0].rect.height
        except Exception as e:
             warnings.warn(f"Could not obtain page height via fitz: {str(e)}", UserWarning)
             return result

        # Camelot uses 1-based indexing for page selection.
        camelot_page_str = str(page_index_0 + 1)
        
        # We use 'stream' flavor for NRC financial/borderless tables as requested.
        # EXECUTION: Single-pass call.
        tables = camelot.read_pdf(
            path_to_process, 
            pages=camelot_page_str, 
            flavor='stream',
            suppress_stdout=True
        )
        
        for i, table in enumerate(tables):
            # 1. Calculate stable hull from cells (top/bottom/left/right extremes)
            # table.cells is a list of lists: [[Cell, Cell], [Cell, Cell]]
            # Each cell has x1, y1, x2, y2 in PDF space (bottom-left origin).
            x_coords = []
            y_coords = []
            valid_cells = 0
            
            for row in table.cells:
                for cell in row:
                    # Capture extremes of the individual cell
                    x_coords.extend([cell.x1, cell.x2])
                    y_coords.extend([cell.y1, cell.y2])
                    valid_cells += 1
            
            if not valid_cells:
                continue
                
            c_x1, c_y1 = min(x_coords), min(y_coords)
            c_x2, c_y2 = max(x_coords), max(y_coords)
            
            # 2. Normalizing text for Markdown row integrity.
            table_text_lines = []
            for _, row in table.df.iterrows():
                clean_row = [str(cell or "").replace("\n", " ").strip() for cell in row]
                table_text_lines.append("| " + " | ".join(clean_row) + " |")
            
            table_markdown = "\n".join(table_text_lines)
            
            # 3. Convert to PyMuPDF top-left [x0, y0, x1, y1]:
            # x0, x1 = x1, x2
            # y0 = height - c_y2 (top boundary)
            # y1 = height - c_y1 (bottom boundary)
            f_x0 = c_x1
            f_y0 = page_height - c_y2
            f_x1 = c_x2
            f_y1 = page_height - c_y1
            
            bbox = [float(f_x0), float(f_y0), float(f_x1), float(f_y1)]
            
            result["tables"].append({
                "page_number": page_index_0 + 1,
                "unit_kind": "pdf_table",
                "text": table_markdown,
                "bbox": bbox,
            })
            result["exclusion_bboxes"].append(bbox)
            
    except (ImportError, OSError) as e:
        warnings.warn(f"Camelot/Ghostscript failure: {str(e)}", UserWarning)
    except Exception as e:
        warnings.warn(f"Advanced table extraction failed: {str(e)}", UserWarning)
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except OSError:
                pass
                
    return result
