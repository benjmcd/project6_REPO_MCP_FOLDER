from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.services.review_nrc_aps_candidate_b_trace as trace_service
from cb_trace_fixture import write_candidate_b_trace_bundle


def test_compose_candidate_b_trace_manifest_resolves_valid_bundle_fixture(tmp_path: Path) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path)

    manifest = trace_service.compose_candidate_b_trace_manifest(
        candidate_b_bundle_id=fixture["bundle_id"],
        fixture_id=fixture["fixture_id"],
        checkout_root=fixture["checkout_root"],
    )

    assert manifest.candidate_b_bundle_id == fixture["bundle_id"]
    assert manifest.fixture_id == fixture["fixture_id"]
    assert manifest.identity.bundle_id == fixture["bundle_id"]
    assert manifest.default_tab == "annotated_pdf"
    assert manifest.artifacts.annotated_pdf is not None
    assert manifest.artifacts.raw_json is not None
    assert manifest.artifacts.raw_markdown is not None
    assert "footer_warning" in manifest.warnings
    assert "labels_sidecar_manifest_hash_status" not in manifest.warnings


def test_compose_candidate_b_trace_manifest_degrades_when_annotated_pdf_missing(tmp_path: Path) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path, include_annotated_pdf=False, annotated_pdf_status="missing")

    manifest = trace_service.compose_candidate_b_trace_manifest(
        candidate_b_bundle_id=fixture["bundle_id"],
        fixture_id=fixture["fixture_id"],
        checkout_root=fixture["checkout_root"],
    )

    assert manifest.default_tab == "summary"
    assert manifest.artifacts.annotated_pdf is None
    annotated_tab = next(tab for tab in manifest.tabs if tab.tab_id == "annotated_pdf")
    assert annotated_tab.available is False
    with pytest.raises(FileNotFoundError, match="annotated_pdf_unavailable"):
        trace_service.resolve_candidate_b_trace_annotated_pdf_info(
            candidate_b_bundle_id=fixture["bundle_id"],
            fixture_id=fixture["fixture_id"],
            checkout_root=fixture["checkout_root"],
        )


def test_candidate_b_trace_service_rejects_raw_ref_outside_validated_raw_root(tmp_path: Path) -> None:
    fixture = write_candidate_b_trace_bundle(
        tmp_path,
        raw_json_ref_override="archive/20260413-cb-proof/cb-proof-test/proof.json",
    )

    with pytest.raises(ValueError, match="candidate_b_raw_json_invalid"):
        trace_service.load_candidate_b_trace_raw_json(
            candidate_b_bundle_id=fixture["bundle_id"],
            fixture_id=fixture["fixture_id"],
            checkout_root=fixture["checkout_root"],
        )


def test_candidate_b_trace_service_rejects_invalid_bundle_id(tmp_path: Path) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path)

    with pytest.raises(ValueError, match="candidate_b_bundle_id_invalid"):
        trace_service.compose_candidate_b_trace_manifest(
            candidate_b_bundle_id="../bad",
            fixture_id=fixture["fixture_id"],
            checkout_root=fixture["checkout_root"],
        )
