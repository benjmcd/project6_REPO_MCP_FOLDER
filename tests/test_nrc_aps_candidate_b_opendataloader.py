from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import support_nrc_aps_candidate_b_opendataloader as support  # noqa: E402
from support_nrc_aps_candidate_b_opendataloader import (  # noqa: E402
    build_odl_cli_capability_snapshot,
    canonical_annotated_pdf_path,
    collect_footer_pages,
    detect_layout_multi_column_signal,
    find_image_source_collisions,
    run_candidate_b_cli,
    summarize_candidate_output,
)


def test_collect_footer_pages_tracks_page_numbers() -> None:
    payload = {
        "kids": [
            {
                "type": "footer",
                "page number": 2,
                "kids": [
                    {"type": "heading", "page number": 2, "content": "ii"},
                ],
            },
            {
                "type": "paragraph",
                "page number": 1,
                "content": "alpha",
            },
            {
                "type": "footer",
                "page number": 4,
                "content": "appendix",
            },
        ]
    }

    result = collect_footer_pages(payload)

    assert result == {
        "count": 2,
        "pages": [2, 4],
    }


def test_find_image_source_collisions_detects_shared_paths() -> None:
    result = find_image_source_collisions(
        {
            "ml17123a319": ["images/ml17123a319/imageFile1.png"],
            "layout": [],
            "scanned": ["images/scanned/imageFile1.png"],
            "mixed": ["images/shared/imageFile1.png"],
            "fontish": ["images/shared/imageFile1.png"],
        }
    )

    assert result == [
        {
            "fixture_ids": ["fontish", "mixed"],
            "source": "images/shared/imageFile1.png",
        }
    ]


def test_detect_layout_multi_column_signal_finds_horizontal_separation() -> None:
    payload = {
        "kids": [
            {
                "type": "paragraph",
                "page number": 1,
                "bounding box": [72.0, 120.0, 250.0, 220.0],
                "content": "left column",
            },
            {
                "type": "paragraph",
                "page number": 1,
                "bounding box": [320.0, 130.0, 520.0, 225.0],
                "content": "right column",
            },
        ]
    }

    assert detect_layout_multi_column_signal(payload) is True


def test_build_odl_cli_capability_snapshot_requires_pdf_support(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        support,
        "run_shell_command",
        lambda command, *, cwd, env: {
            "args": command,
            "cwd": str(cwd),
            "exit_code": 0,
            "stdout": "--format FORMAT  Output formats (comma-separated). Values: json, markdown",
            "stderr": "",
            "passed": True,
        },
    )

    with pytest.raises(RuntimeError, match="annotated_pdf_output_unsupported"):
        build_odl_cli_capability_snapshot()


def test_run_candidate_b_cli_uses_direct_convert_and_canonicalizes_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    fixture_path = corpus_dir / "fontish.pdf"
    fixture_path.write_bytes(b"%PDF-1.4\n%fixture\n")
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    monkeypatch.setattr(support, "CORPUS_DIR", corpus_dir)

    def _fake_convert(**kwargs):
        assert kwargs["format"] == "json,markdown,pdf"
        assert kwargs["output_dir"] == str(raw_root)
        assert kwargs["image_output"] == "external"
        output_dir = Path(kwargs["output_dir"])
        (output_dir / "fontish.json").write_text(json.dumps({"kids": [], "number of pages": 1}), encoding="utf-8")
        (output_dir / "fontish.md").write_text("# fontish", encoding="utf-8")
        (output_dir / "fontish.pdf").write_bytes(b"%PDF-1.4\n%annotated\n")
        print("ok")

    monkeypatch.setitem(sys.modules, "opendataloader_pdf", types.SimpleNamespace(convert=_fake_convert))

    cli_result, _ = run_candidate_b_cli(
        fixture_entry={"fixture_id": "fontish", "path": "fontish.pdf"},
        raw_root=raw_root,
    )

    canonical_path = canonical_annotated_pdf_path(raw_root, "fontish")
    assert canonical_path.exists()
    assert not (raw_root / "fontish.pdf").exists()
    assert cli_result["invocation"] == "opendataloader_pdf.convert"
    assert cli_result["stdout"] == "ok\n"
    assert cli_result["annotated_pdf_ref"].endswith("annotated/fontish.pdf")


def test_summarize_candidate_output_emits_annotated_pdf_refs(tmp_path: Path) -> None:
    raw_json_path = tmp_path / "fontish.json"
    raw_markdown_path = tmp_path / "fontish.md"
    annotated_pdf_path = canonical_annotated_pdf_path(tmp_path, "fontish")
    annotated_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    raw_json_path.write_text(
        json.dumps(
            {
                "file name": "fontish.pdf",
                "number of pages": 1,
                "kids": [
                    {
                        "type": "heading",
                        "page number": 1,
                        "content": "Intro",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    raw_markdown_path.write_text("# Intro", encoding="utf-8")
    annotated_pdf_path.write_bytes(b"%PDF-1.4\n%annotated\n")

    summary = summarize_candidate_output(
        fixture_id="fontish",
        label_entry={"regime_labels": []},
        raw_json_path=raw_json_path,
        raw_markdown_path=raw_markdown_path,
        annotated_pdf_path=annotated_pdf_path,
        log_text="",
    )

    assert summary["annotated_pdf_status"] == "present"
    assert summary["annotated_pdf_ref"].endswith("annotated/fontish.pdf")
    assert summary["annotated_pdf_sha256"]
