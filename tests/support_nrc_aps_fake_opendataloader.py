from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any


def install_fake_opendataloader_pdf(monkeypatch: Any, document_processing_module: Any, *, version: str | None = None) -> None:
    """Install a deterministic fake for positive Candidate B extractor tests."""
    expected_version = version or document_processing_module.APS_ODL_PDF_EXPECTED_VERSION
    real_version = document_processing_module.importlib.metadata.version

    def _version(dist_name: str) -> str:
        if dist_name == "opendataloader-pdf":
            return expected_version
        return real_version(dist_name)

    def _convert(*, input_path: str, output_dir: str, format: str, **_kwargs: Any) -> None:
        if format != "json":
            raise ValueError("fake_opendataloader_only_supports_json")
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "number of pages": 1,
            "kids": [
                {
                    "type": "paragraph",
                    "page number": 1,
                    "content": (
                        "Reactor coolant pump inspection notes identify "
                        "deterministic candidate b text extraction output."
                    ),
                    "bounding box": [10, 20, 300, 60],
                }
            ],
            "source": Path(input_path).name,
        }
        (output_root / "input.json").write_text(json.dumps(payload), encoding="utf-8")

    fake_module = types.ModuleType("opendataloader_pdf")
    fake_module.convert = _convert
    monkeypatch.setattr(document_processing_module.importlib.metadata, "version", _version)
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", fake_module)
