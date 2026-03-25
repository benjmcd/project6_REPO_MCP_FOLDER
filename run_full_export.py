"""NRC ADAMS Full Document Export — processes all 43 PDFs and produces
content-addressed blobs, normalized text, diagnostics, visual page artifacts,
and summary files."""

import sys
from pathlib import Path
import hashlib
import json
import uuid
import os
from datetime import datetime, timezone

sys.path.insert(0, "backend")

from app.services import nrc_aps_document_processing


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_target_id(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:80]


def process_nrc_documents():
    output_dir = Path("nrc_adams_full_export")
    source_dir = Path("data_demo/nrc_adams_documents_for_testing")

    # Clean start
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    # Create directory structure
    for sub in [
        "nrc_adams_aps/blobs/sha256",
        "nrc_adams_aps/normalized_text",
        "nrc_adams_aps/diagnostics",
        "nrc_adams_aps/visual_pages/sha256",
        "reports",
    ]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)

    run_id = f"full_export_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    config = nrc_aps_document_processing.default_processing_config({
        "artifact_storage_dir": str(output_dir),
        "visual_render_dpi": 150,
        "ocr_enabled": False,
    })

    pdf_files = sorted(source_dir.rglob("*.pdf"))
    results = []
    stats = {
        "total": len(pdf_files),
        "success": 0,
        "failed": 0,
        "total_pages": 0,
        "visual_artifacts": 0,
        "total_blob_bytes": 0,
        "total_text_chars": 0,
    }

    for i, pdf_path in enumerate(pdf_files, 1):
        category = pdf_path.parent.name.replace("_documents_for_testing", "").replace("_for_testing", "")
        print(f"\n[{i:>2}/{len(pdf_files)}] {pdf_path.name[:70]}")
        print(f"       Category: {category}")

        target_id = safe_target_id(pdf_path.stem)

        try:
            pdf_bytes = pdf_path.read_bytes()
            pdf_sha = sha256_bytes(pdf_bytes)

            # 1. Store blob (content-addressed PDF)
            blob_rel = f"nrc_adams_aps/blobs/sha256/{pdf_sha[0:2]}/{pdf_sha[2:4]}/{pdf_sha}.pdf"
            blob_abs = output_dir / blob_rel
            blob_abs.parent.mkdir(parents=True, exist_ok=True)
            if not blob_abs.exists():
                blob_abs.write_bytes(pdf_bytes)

            # 2. Process document
            result = nrc_aps_document_processing._process_pdf(
                content=pdf_bytes,
                detection={
                    "effective_content_type": "application/pdf",
                    "supported_for_processing": True,
                    "filename": pdf_path.name,
                },
                config=config,
                deadline=None,
            )

            # 3. Store normalized text (content-addressed)
            text = result.get("normalized_text", "")
            text_ref = None
            text_sha = None
            if text.strip():
                text_bytes = text.encode("utf-8")
                text_sha = sha256_bytes(text_bytes)
                text_rel = f"nrc_adams_aps/normalized_text/{text_sha[0:2]}/{text_sha[2:4]}/{text_sha}.txt"
                text_abs = output_dir / text_rel
                text_abs.parent.mkdir(parents=True, exist_ok=True)
                if not text_abs.exists():
                    text_abs.write_bytes(text_bytes)
                text_ref = text_rel

            # 4. Store diagnostics
            visual_page_refs = result.get("visual_page_refs", [])
            diag = {
                "schema_id": "aps.document_processing_diagnostics.v1",
                "schema_version": 1,
                "run_id": run_id,
                "target_id": target_id,
                "processed_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_file": str(pdf_path),
                "source_sha256": pdf_sha,
                "source_bytes": len(pdf_bytes),
                "blob_ref": blob_rel,
                "normalized_text_ref": text_ref,
                "normalized_text_sha256": text_sha,
                "processing_result": {
                    "page_count": result.get("page_count", 0),
                    "quality_status": result.get("quality_status"),
                    "document_class": result.get("document_class"),
                    "extractor_id": result.get("extractor_id"),
                    "extractor_version": result.get("extractor_version"),
                    "normalized_char_count": result.get("normalized_char_count", 0),
                    "degradation_codes": result.get("degradation_codes", []),
                    "visual_page_refs_count": len(visual_page_refs),
                },
                "page_summaries": result.get("page_summaries", []),
                "visual_page_refs": visual_page_refs,
            }
            diag_name = f"{run_id}_{target_id}_document_processing_v1.json"
            diag_path = output_dir / "nrc_adams_aps" / "diagnostics" / diag_name
            diag_path.write_text(json.dumps(diag, indent=2, default=str), encoding="utf-8")

            # Update stats
            page_count = result.get("page_count", 0)
            visual_count = len(visual_page_refs)
            stats["success"] += 1
            stats["total_pages"] += page_count
            stats["visual_artifacts"] += visual_count
            stats["total_blob_bytes"] += len(pdf_bytes)
            stats["total_text_chars"] += len(text)

            results.append({
                "file": pdf_path.name,
                "category": category,
                "target_id": target_id,
                "status": "success",
                "source_sha256": pdf_sha,
                "blob_ref": blob_rel,
                "normalized_text_ref": text_ref,
                "pages": page_count,
                "quality": result.get("quality_status"),
                "document_class": result.get("document_class"),
                "visuals": visual_count,
                "degradation_codes": result.get("degradation_codes", []),
                "char_count": len(text),
            })

            visual_str = f", Visuals: {visual_count}" if visual_count else ""
            print(f"       Pages: {page_count}, Quality: {result.get('quality_status')}, Chars: {len(text):,}{visual_str}")

        except Exception as e:
            stats["failed"] += 1
            results.append({
                "file": pdf_path.name,
                "category": category,
                "target_id": target_id,
                "status": "failed",
                "error": str(e),
            })
            print(f"       ERROR: {e}")

    # 5. Write run report
    run_report = {
        "schema_id": "aps.full_export_run.v1",
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "source_directory": str(source_dir),
        "output_directory": str(output_dir),
        "statistics": stats,
    }
    run_report_path = output_dir / "reports" / f"{run_id}_run_v1.json"
    run_report_path.write_text(json.dumps(run_report, indent=2, default=str), encoding="utf-8")

    # 6. Write manifest
    manifest = {
        "schema_id": "aps.full_export_manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "source_directory": str(source_dir),
        "output_directory": str(output_dir),
        "statistics": stats,
        "documents": results,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )

    # 7. Write human-readable summary
    with open(output_dir / "processing_summary.txt", "w", encoding="utf-8") as f:
        f.write("=" * 90 + "\n")
        f.write("NRC ADAMS DOCUMENT PROCESSING — FULL EXPORT\n")
        f.write("=" * 90 + "\n\n")
        f.write(f"Generated:  {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Run ID:     {run_id}\n")
        f.write(f"Source:     {source_dir}\n")
        f.write(f"Output:     {output_dir}\n\n")
        f.write("STATISTICS\n")
        f.write("-" * 50 + "\n")
        f.write(f"Total documents:    {stats['total']}\n")
        f.write(f"Successful:         {stats['success']}\n")
        f.write(f"Failed:             {stats['failed']}\n")
        f.write(f"Total pages:        {stats['total_pages']}\n")
        f.write(f"Visual artifacts:   {stats['visual_artifacts']}\n")
        f.write(f"Total blob bytes:   {stats['total_blob_bytes']:,}\n")
        f.write(f"Total text chars:   {stats['total_text_chars']:,}\n\n")

        # Quality distribution
        quality_counts = {}
        for r in results:
            if r["status"] == "success":
                q = r.get("quality", "unknown")
                quality_counts[q] = quality_counts.get(q, 0) + 1
        f.write("QUALITY DISTRIBUTION\n")
        f.write("-" * 50 + "\n")
        for q in ["strong", "limited", "weak", "unusable"]:
            f.write(f"  {q:<12} {quality_counts.get(q, 0)}\n")
        f.write("\n")

        # Per-category
        cat_counts = {}
        for r in results:
            cat = r.get("category", "unknown")
            if cat not in cat_counts:
                cat_counts[cat] = {"total": 0, "success": 0, "pages": 0, "visuals": 0}
            cat_counts[cat]["total"] += 1
            if r["status"] == "success":
                cat_counts[cat]["success"] += 1
                cat_counts[cat]["pages"] += r.get("pages", 0)
                cat_counts[cat]["visuals"] += r.get("visuals", 0)
        f.write("BY CATEGORY\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'Category':<55} {'Docs':>4} {'Pages':>6} {'Visuals':>8}\n")
        f.write("-" * 90 + "\n")
        for cat in sorted(cat_counts):
            c = cat_counts[cat]
            f.write(f"  {cat:<53} {c['total']:>4} {c['pages']:>6} {c['visuals']:>8}\n")
        f.write("\n")

        # Per-document detail
        f.write("DOCUMENTS\n")
        f.write("-" * 90 + "\n")
        for r in results:
            status = "OK  " if r["status"] == "success" else "FAIL"
            name = r["file"][:55]
            if r["status"] == "success":
                f.write(
                    f"[{status}] {name:<55} pg={r['pages']:>3}  vis={r['visuals']:>2}  q={r['quality']}\n"
                )
            else:
                f.write(f"[{status}] {name:<55} ERROR: {r.get('error', 'unknown')[:30]}\n")

    print(f"\n{'=' * 90}")
    print("EXPORT COMPLETE")
    print(f"{'=' * 90}")
    print(f"Output:           {output_dir}")
    print(f"Successful:       {stats['success']}/{stats['total']}")
    print(f"Failed:           {stats['failed']}")
    print(f"Total pages:      {stats['total_pages']}")
    print(f"Visual artifacts: {stats['visual_artifacts']}")
    print(f"Total text chars: {stats['total_text_chars']:,}")
    return stats


if __name__ == "__main__":
    process_nrc_documents()
