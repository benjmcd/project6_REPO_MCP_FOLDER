from __future__ import annotations

import sys
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from support_nrc_aps_candidate_b_opendataloader import (  # noqa: E402
    collect_footer_pages,
    detect_layout_multi_column_signal,
    find_image_source_collisions,
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
