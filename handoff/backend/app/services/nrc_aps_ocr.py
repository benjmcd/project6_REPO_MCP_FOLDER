from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any


class OcrUnavailableError(RuntimeError):
    pass


class OcrExecutionError(RuntimeError):
    pass


def _resolve_tesseract_executable() -> str | None:
    configured = str(os.environ.get("TESSERACT_CMD") or "").strip()
    if configured:
        candidate = Path(configured)
        if candidate.exists():
            return str(candidate)
        resolved = shutil.which(configured)
        if resolved:
            return str(resolved)

    resolved = shutil.which("tesseract")
    if resolved:
        return str(resolved)

    windows_candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in windows_candidates:
        if candidate.exists():
            return str(candidate)
    return None


def tesseract_available() -> bool:
    return bool(_resolve_tesseract_executable())


def run_tesseract_ocr(
    *,
    image_bytes: bytes,
    language: str = "eng",
    dpi: int = 300,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    executable = _resolve_tesseract_executable()
    if not executable:
        raise OcrUnavailableError("tesseract_not_installed")

    with tempfile.TemporaryDirectory(prefix="apsocr") as temp_dir:
        temp_root = Path(temp_dir)
        image_path = temp_root / "page.png"
        output_base = temp_root / "page_ocr"
        image_path.write_bytes(bytes(image_bytes or b""))
        command = [
            executable,
            str(image_path),
            str(output_base),
            "-l",
            str(language or "eng"),
            "--dpi",
            str(int(dpi)),
            "--oem",
            "1",
            "--psm",
            "6",
            "tsv",
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=int(timeout_seconds),
            )
        except subprocess.TimeoutExpired as exc:
            raise OcrExecutionError("tesseract_timeout") from exc
        if completed.returncode != 0:
            stderr = str(completed.stderr or "").strip()
            raise OcrExecutionError(stderr or "tesseract_failed")

        tsv_path = output_base.with_suffix(".tsv")
        if not tsv_path.exists():
            raise OcrExecutionError("tesseract_output_missing")
        text, average_confidence, rows = _parse_tesseract_tsv(tsv_path.read_text(encoding="utf-8", errors="replace"))
        return {
            "text": text,
            "average_confidence": average_confidence,
            "rows": rows,
            "engine": "tesseract_cli",
            "language": str(language or "eng"),
            "dpi": int(dpi),
        }


def _parse_tesseract_tsv(tsv_text: str) -> tuple[str, float | None, list[dict[str, Any]]]:
    reader = csv.DictReader(StringIO(str(tsv_text or "")), delimiter="\t")
    words: list[str] = []
    confidences: list[float] = []
    rows: list[dict[str, Any]] = []
    for row in reader:
        text = str(row.get("text") or "").strip()
        conf_raw = str(row.get("conf") or "").strip()
        confidence: float | None = None
        if conf_raw not in {"", "-1"}:
            try:
                confidence = float(conf_raw)
            except ValueError:
                confidence = None
        if text:
            words.append(text)
        if confidence is not None:
            confidences.append(confidence)
        if text or confidence is not None:
            rows.append(
                {
                    "text": text,
                    "confidence": confidence,
                    "left": _safe_int(row.get("left")),
                    "top": _safe_int(row.get("top")),
                    "width": _safe_int(row.get("width")),
                    "height": _safe_int(row.get("height")),
                }
            )
    average_confidence = (sum(confidences) / len(confidences)) if confidences else None
    return " ".join(words).strip(), average_confidence, rows


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
