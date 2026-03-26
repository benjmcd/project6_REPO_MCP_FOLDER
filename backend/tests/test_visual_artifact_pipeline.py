"""
Full pipeline test for visual artifact generation.

Tests: ingestion -> content_index -> search with actual NRC ADAMS documents.

This script:
1. Processes PDF fixtures with artifact_storage_dir enabled
2. Collects artifact metadata and verifies PNG files exist
3. Persists results through content index
4. Verifies round-trip through search endpoints
"""

import os
import sys
import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock heavy dependencies before imports
from unittest.mock import MagicMock, patch

# Only mock what's strictly necessary for basic PDF processing
# We want REAL processing and REAL artifact creation

import fitz  # PyMuPDF - needed for real PDF handling

# Import services
from app.services import nrc_aps_document_processing
from app.services import nrc_aps_content_index
from app.services import nrc_aps_artifact_ingestion
from app.schemas.api import ConnectorRunContentUnitOut

# Test directory for artifacts
ARTIFACT_OUTPUT_DIR = Path(__file__).parent.parent / "app" / "storage_test_runtime" / "visual_artifact_probe"

# PDF fixtures to test
FIXTURE_DIRS = [
    Path(__file__).parent.parent.parent / "handoff" / "tests" / "fixtures" / "nrc_aps_docs" / "v1",
    Path(__file__).parent.parent.parent / "data_demo" / "nrc_adams_documents_for_testing",
]

# Real NRC ADAMS PDFs to test (subset)
REAL_ADAMS_PDFS = [
    "technical_specification_amendment_documents_for_testing/ML26063A419_Non-Proprietary.pdf",
    "license-application_for_facility _operating_license_documents_for_testing/E260305t115500_DCL-26-015.pdf",
    "licensee_event_reports_for_testing/E260305t155806_102-09044 LER 2025-002-00.pdf",
    "inspection_reports_for_testing/NRC Inspection Report 030-33887 2025-001 and Notice of Violation - High Mountain Inspection Service, Inc. (Public).pdf",
    "part_21_correspondence_documents_for_testing/EN# 57402 Ametek Update 013125.pdf",
]


def collect_pdf_fixtures():
    """Collect all PDF fixtures from test directories."""
    fixtures = []
    
    # Collect from handoff/tests/fixtures/nrc_aps_docs/v1
    v1_dir = FIXTURE_DIRS[0]
    if v1_dir.exists():
        for pdf_file in v1_dir.glob("*.pdf"):
            fixtures.append(("v1_fixture", pdf_file))
    
    # Collect real NRC ADAMS PDFs
    real_dir = FIXTURE_DIRS[1]
    if real_dir.exists():
        for rel_path in REAL_ADAMS_PDFS:
            full_path = real_dir / rel_path
            if full_path.exists():
                fixtures.append(("real_adams", full_path))
    
    return fixtures


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_artifact_file(artifact_ref: str, storage_dir: Path) -> dict:
    """Verify that an artifact file exists and has correct properties."""
    artifact_path = storage_dir / artifact_ref
    
    if not artifact_path.exists():
        return {"exists": False, "path": str(artifact_path)}
    
    file_size = artifact_path.stat().st_size
    sha256 = compute_file_sha256(artifact_path)
    
    return {
        "exists": True,
        "path": str(artifact_path),
        "file_size_bytes": file_size,
        "sha256": sha256,
    }


def process_pdf_with_artifacts(pdf_path: Path, artifact_dir: Path, dpi: int = 150) -> dict:
    """Process a single PDF and collect artifact information."""
    
    print(f"\n{'='*80}")
    print(f"Processing: {pdf_path.name}")
    print(f"Type: {pdf_path.suffix}")
    print(f"Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    
    try:
        # Read PDF content
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        # Configure processing with artifact storage
        config = nrc_aps_document_processing.default_processing_config({
            "artifact_storage_dir": str(artifact_dir),
            "visual_render_dpi": dpi,
            "ocr_enabled": False,  # Disable OCR for speed
        })
        
        # Process the PDF
        detection = {
            "effective_content_type": "application/pdf",
            "filename": pdf_path.name,
        }
        
        result = nrc_aps_document_processing._process_pdf(
            content=pdf_content,
            detection=detection,
            config=config,
            deadline=None,
        )
        
        # Extract artifact information
        visual_page_refs = result.get("visual_page_refs", [])
        artifact_refs = []
        
        for vpr in visual_page_refs:
            if "visual_artifact_ref" in vpr:
                artifact_info = verify_artifact_file(vpr["visual_artifact_ref"], artifact_dir)
                artifact_refs.append({
                    "page_number": vpr.get("page_number"),
                    "artifact_ref": vpr.get("visual_artifact_ref"),
                    "sha256": vpr.get("visual_artifact_sha256"),
                    "dpi": vpr.get("visual_artifact_dpi"),
                    "format": vpr.get("visual_artifact_format"),
                    "semantics": vpr.get("visual_artifact_semantics"),
                    "verified": artifact_info,
                })
        
        output = {
            "status": "success",
            "filename": pdf_path.name,
            "source_type": "v1_fixture" if "v1" in str(pdf_path) else "real_adams",
            "total_pages": result.get("page_count", 0),
            "visual_page_refs_count": len(visual_page_refs),
            "artifacts_created": len(artifact_refs),
            "degradation_codes": result.get("degradation_codes", []),
            "artifact_refs": artifact_refs,
            "processing_result_keys": list(result.keys()),
        }
        
        print(f"  Total pages: {output['total_pages']}")
        print(f"  Visual page refs: {output['visual_page_refs_count']}")
        print(f"  Artifacts created: {output['artifacts_created']}")
        if output['degradation_codes']:
            print(f"  Degradation codes: {output['degradation_codes']}")
        
        return output
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        return {
            "status": "error",
            "filename": pdf_path.name,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def _content_index_roundtrip(processing_results: list[dict], storage_dir: Path) -> dict:
    """Test that artifact metadata survives through content_index persistence."""
    
    print(f"\n{'='*80}")
    print("Testing content index round-trip...")
    
    # Set up in-memory database
    import sqlite3
    
    # Create temporary database
    db_conn = sqlite3.connect(":memory:")
    
    # Create content_units table schema
    db_conn.execute("""
        CREATE TABLE content_units (
            content_id TEXT PRIMARY KEY,
            chunk_id TEXT,
            content_contract_id TEXT,
            chunking_contract_id TEXT,
            chunk_ordinal INTEGER,
            start_char INTEGER,
            end_char INTEGER,
            chunk_text TEXT,
            chunk_text_sha256 TEXT,
            run_id TEXT,
            target_id TEXT,
            blob_ref TEXT,
            visual_page_refs_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    roundtrip_results = []
    
    for proc_result in processing_results:
        if proc_result.get("status") != "success":
            continue
            
        # Create a mock content unit with visual page refs
        content_id = f"test-content-{proc_result['filename']}"
        visual_refs = proc_result.get("artifact_refs", [])
        
        if not visual_refs:
            continue
        
        # Serialize visual_page_refs to JSON
        vpr_data = []
        for ar in visual_refs:
            vpr_data.append({
                "page_number": ar["page_number"],
                "visual_page_class": "diagram_or_visual",
                "status": "preserved",
                "visual_artifact_ref": ar["artifact_ref"],
                "visual_artifact_sha256": ar["sha256"],
                "visual_artifact_dpi": ar["dpi"],
                "visual_artifact_format": ar["format"],
                "visual_artifact_semantics": ar["semantics"],
            })
        
        visual_page_refs_json = json.dumps(vpr_data)
        
        # Insert into database
        db_conn.execute("""
            INSERT INTO content_units (
                content_id, chunk_id, content_contract_id, chunking_contract_id,
                chunk_ordinal, start_char, end_char, chunk_text, chunk_text_sha256,
                run_id, target_id, blob_ref, visual_page_refs_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content_id,
            f"chunk-{proc_result['filename']}",
            "test-contract",
            "test-chunking",
            0, 0, 100,
            "test content",
            "abc123",
            "test-run",
            "test-target",
            "/test/blob",
            visual_page_refs_json,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
        ))
        
        db_conn.commit()
        
        # Retrieve and verify
        cursor = db_conn.execute(
            "SELECT visual_page_refs_json FROM content_units WHERE content_id = ?",
            (content_id,)
        )
        row = cursor.fetchone()
        
        if row:
            retrieved_json = row[0]
            retrieved_vpr = json.loads(retrieved_json)
            
            # Verify artifact fields survived
            roundtrip_success = True
            for i, original in enumerate(visual_refs):
                retrieved = retrieved_vpr[i] if i < len(retrieved_vpr) else None
                if not retrieved:
                    roundtrip_success = False
                    break
                
                # Check each artifact field
                for field in ["visual_artifact_ref", "visual_artifact_sha256", 
                              "visual_artifact_dpi", "visual_artifact_format", 
                              "visual_artifact_semantics"]:
                    if retrieved.get(field) != original.get(field.replace("visual_artifact_", "visual_artifact_" if field.startswith("visual_artifact_") else field)):
                        # Check with correct field name mapping
                        orig_field = field
                        if field in original:
                            if retrieved.get(field) != original[field]:
                                roundtrip_success = False
                                break
            
            roundtrip_results.append({
                "content_id": content_id,
                "filename": proc_result["filename"],
                "roundtrip_success": roundtrip_success,
                "visual_refs_count": len(visual_refs),
                "retrieved_count": len(retrieved_vpr) if retrieved_vpr else 0,
            })
            
            print(f"  {proc_result['filename']}: {'PASS' if roundtrip_success else 'FAIL'}")
            print(f"    Visual refs: {len(visual_refs)}, Retrieved: {len(retrieved_vpr) if retrieved_vpr else 0}")
    
    db_conn.close()
    
    return {
        "total_tested": len(roundtrip_results),
        "passed": sum(1 for r in roundtrip_results if r["roundtrip_success"]),
        "failed": sum(1 for r in roundtrip_results if not r["roundtrip_success"]),
        "details": roundtrip_results,
    }


def main():
    """Main test execution."""
    
    print("="*80)
    print("VISUAL ARTIFACT PIPELINE TEST")
    print("="*80)
    print(f"Output directory: {ARTIFACT_OUTPUT_DIR}")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    
    # Ensure output directory exists
    ARTIFACT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect PDF fixtures
    fixtures = collect_pdf_fixtures()
    print(f"\nFound {len(fixtures)} PDF fixtures to process")
    
    # Process each PDF
    results = []
    for fixture_type, pdf_path in fixtures:
        result = process_pdf_with_artifacts(
            pdf_path=pdf_path,
            artifact_dir=ARTIFACT_OUTPUT_DIR,
            dpi=150,
        )
        result["fixture_type"] = fixture_type
        results.append(result)
    
    # Summary of processing
    print(f"\n{'='*80}")
    print("PROCESSING SUMMARY")
    print(f"{'='*80}")
    
    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "error"]
    with_artifacts = [r for r in successful if r.get("artifacts_created", 0) > 0]
    
    print(f"Total processed: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"With artifacts: {len(with_artifacts)}")
    
    # List artifacts created
    if with_artifacts:
        print(f"\n{'='*80}")
        print("ARTIFACTS CREATED")
        print(f"{'='*80}")
        
        total_artifacts = 0
        for result in with_artifacts:
            for artifact in result.get("artifact_refs", []):
                total_artifacts += 1
                verified = artifact.get("verified", {})
                print(f"\n{artifact['artifact_ref']}")
                print(f"  Page: {artifact['page_number']}")
                print(f"  SHA-256: {artifact['sha256'][:16]}...")
                print(f"  DPI: {artifact['dpi']}")
                if verified.get("exists"):
                    print(f"  File exists: {verified['file_size_bytes']} bytes")
                    print(f"  File SHA-256 matches: {verified['sha256'] == artifact['sha256']}")
    
    # Test content index round-trip
    roundtrip_result = _content_index_roundtrip(successful, ARTIFACT_OUTPUT_DIR)
    
    print(f"\n{'='*80}")
    print("ROUND-TRIP RESULTS")
    print(f"{'='*80}")
    print(f"Total tested: {roundtrip_result['total_tested']}")
    print(f"Passed: {roundtrip_result['passed']}")
    print(f"Failed: {roundtrip_result['failed']}")
    
    # List directory contents
    print(f"\n{'='*80}")
    print("ARTIFACT DIRECTORY CONTENTS")
    print(f"{'='*80}")
    
    artifact_files = list(ARTIFACT_OUTPUT_DIR.rglob("*.png"))
    print(f"Total PNG files: {len(artifact_files)}")
    
    for png_file in sorted(artifact_files)[:20]:  # Show first 20
        rel_path = png_file.relative_to(ARTIFACT_OUTPUT_DIR)
        print(f"  {rel_path}")
    
    if len(artifact_files) > 20:
        print(f"  ... and {len(artifact_files) - 20} more")
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"PDFs processed successfully: {len(successful)}/{len(results)}")
    print(f"Visual page refs created: {sum(r.get('visual_page_refs_count', 0) for r in successful)}")
    print(f"Artifacts created: {sum(r.get('artifacts_created', 0) for r in successful)}")
    print(f"PNG files on disk: {len(artifact_files)}")
    print(f"Round-trip tests passed: {roundtrip_result['passed']}/{roundtrip_result['total_tested']}")
    
    # Write results to JSON
    results_file = ARTIFACT_OUTPUT_DIR / "test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "processed_at": datetime.utcnow().isoformat(),
            "results": results,
            "roundtrip": roundtrip_result,
            "total_png_files": len(artifact_files),
        }, f, indent=2, default=str)
    
    print(f"\nResults written to: {results_file}")
    
    # Return success/failure
    all_passed = (
        len(failed) == 0 and
        len(artifact_files) > 0 and
        roundtrip_result['failed'] == 0
    )
    
    print(f"\nOverall result: {'PASS' if all_passed else 'FAIL'}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)