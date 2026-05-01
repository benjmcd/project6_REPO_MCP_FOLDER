from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.review_nrc_aps import (
    NrcApsWorkbenchCompareBadgeOut,
    NrcApsWorkbenchCompareBundleBindingOut,
    NrcApsWorkbenchCompareBundleSourceItemOut,
    NrcApsWorkbenchCompareColumnOut,
    NrcApsWorkbenchCompareDeepLinksOut,
    NrcApsWorkbenchCompareManifestOut,
    NrcApsWorkbenchCompareRunBindingOut,
    NrcApsWorkbenchCompareRunSourceItemOut,
    NrcApsWorkbenchCompareSourceIdentityOut,
    NrcApsWorkbenchCompareSourcesOut,
    NrcApsWorkbenchCompareTabDefOut,
    NrcApsWorkbenchCompareTabOut,
    NrcApsWorkbenchCompareTargetItemOut,
    NrcApsWorkbenchCompareTargetsOut,
    NrcApsWorkbenchCompareVariantBindingsOut,
)
from main import app


client = TestClient(app)


def _sources_payload() -> NrcApsWorkbenchCompareSourcesOut:
    return NrcApsWorkbenchCompareSourcesOut(
        default_baseline_run_id="baseline-run-001",
        default_candidate_a_run_id="candidate-a-run-001",
        default_candidate_b_bundle_id="archive/20260412-cb-proof/cb-proof-test",
        baseline_runs=[
            NrcApsWorkbenchCompareRunSourceItemOut(
                run_id="baseline-run-001",
                display_label="Baseline Run",
                completed_at="2026-04-12T08:00:00Z",
                variant_kind="baseline",
            )
        ],
        candidate_a_runs=[
            NrcApsWorkbenchCompareRunSourceItemOut(
                run_id="candidate-a-run-001",
                display_label="Candidate A Run",
                completed_at="2026-04-12T08:05:00Z",
                variant_kind="candidate_a_page_evidence_v1",
            )
        ],
        candidate_b_bundles=[
            NrcApsWorkbenchCompareBundleSourceItemOut(
                bundle_id="archive/20260412-cb-proof/cb-proof-test",
                display_label="cb-proof-test | workbench_useful_with_explicit_footer_limitation",
                generated_at_utc="2026-04-12T08:00:00Z",
                decision_recommendation="workbench_useful_with_explicit_footer_limitation",
                local_only=True,
            )
        ],
        candidate_b_runtime_runs=[
            NrcApsWorkbenchCompareRunSourceItemOut(
                run_id="candidate-b-runtime-001",
                display_label="Candidate B Runtime",
                completed_at="2026-04-12T08:15:00Z",
                variant_kind="candidate_b_opendataloader_pdf",
            )
        ],
    )


def _targets_payload() -> NrcApsWorkbenchCompareTargetsOut:
    return NrcApsWorkbenchCompareTargetsOut(
        baseline_run_id="baseline-run-001",
        candidate_a_run_id="candidate-a-run-001",
        candidate_b_bundle_id="archive/20260412-cb-proof/cb-proof-test",
        default_fixture_id="fixture-001",
        targets=[
            NrcApsWorkbenchCompareTargetItemOut(
                fixture_id="fixture-001",
                display_label="Fixture 001",
                source_file_name="fixture-001.pdf",
                baseline_target_id="target-baseline-001",
                candidate_a_target_id="target-candidate-a-001",
                candidate_b_available=True,
                comparability_state="aligned",
            )
        ],
    )


def _manifest_payload() -> NrcApsWorkbenchCompareManifestOut:
    return NrcApsWorkbenchCompareManifestOut(
        fixture_id="fixture-001",
        source_identity=NrcApsWorkbenchCompareSourceIdentityOut(
            fixture_id="fixture-001",
            document_title="Fixture 001",
            document_type="report",
            source_file_name="fixture-001.pdf",
            accession_number="LOCALAPS00001",
            document_ref="doc-ref-001",
            document_sha256="sha256-001",
        ),
        variant_bindings=NrcApsWorkbenchCompareVariantBindingsOut(
            baseline=NrcApsWorkbenchCompareRunBindingOut(
                run_id="baseline-run-001",
                target_id="target-baseline-001",
                content_id="content-001",
            ),
            candidate_a=NrcApsWorkbenchCompareRunBindingOut(
                run_id="candidate-a-run-001",
                target_id="target-candidate-a-001",
                content_id="content-001",
            ),
            candidate_b=NrcApsWorkbenchCompareBundleBindingOut(
                bundle_id="archive/20260412-cb-proof/cb-proof-test",
                candidate_b_run_id="cb-run-001",
            ),
        ),
        summary_badges=[
            NrcApsWorkbenchCompareBadgeOut(
                key="candidate_b_decision",
                label="Candidate B",
                value="workbench_useful_with_explicit_footer_limitation",
                severity="warning",
            )
        ],
        tabs=[
            NrcApsWorkbenchCompareTabDefOut(tab_id="summary", label="Summary", available=True),
            NrcApsWorkbenchCompareTabDefOut(tab_id="normalized_text", label="Normalized Text", available=True),
        ],
        warnings=["footer_warning"],
        limitations=["footer_page_numbers_detected"],
        deep_links=NrcApsWorkbenchCompareDeepLinksOut(
            baseline_trace="/review/nrc-aps/document-trace?run_id=baseline-run-001&target_id=target-baseline-001",
            candidate_a_trace="/review/nrc-aps/document-trace?run_id=candidate-a-run-001&target_id=target-candidate-a-001",
            candidate_b_trace="/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=archive%2F20260412-cb-proof%2Fcb-proof-test&fixture_id=fixture-001",
        ),
    )


def _tab_payload() -> NrcApsWorkbenchCompareTabOut:
    return NrcApsWorkbenchCompareTabOut(
        fixture_id="fixture-001",
        tab_id="summary",
        columns={
            "baseline": NrcApsWorkbenchCompareColumnOut(
                variant_id="baseline",
                available=True,
                comparability_class="direct",
                label="Baseline",
                data={"page_count": 4},
            ),
            "candidate_a": NrcApsWorkbenchCompareColumnOut(
                variant_id="candidate_a",
                available=True,
                comparability_class="direct",
                label="Candidate A",
                data={"page_count": 4},
            ),
            "candidate_b": NrcApsWorkbenchCompareColumnOut(
                variant_id="candidate_b",
                available=True,
                comparability_class="direct",
                label="Candidate B",
                data={"page_count": 4},
                warnings=["footer_warning"],
                deep_link="/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=archive%2F20260412-cb-proof%2Fcb-proof-test&fixture_id=fixture-001",
            ),
        },
        comparability_legend={"direct": "Directly comparable against the owner-path variants."},
        warnings=["footer_warning"],
        limitations=["footer_page_numbers_detected"],
    )


@patch("app.api.review_nrc_aps.discover_workbench_compare_sources")
def test_workbench_compare_sources_route(mock_sources) -> None:
    mock_sources.return_value = _sources_payload()

    response = client.get("/api/v1/review/nrc-aps/workbench-compare/sources")

    assert response.status_code == 200
    data = response.json()
    assert data["default_baseline_run_id"] == "baseline-run-001"
    assert data["candidate_b_bundles"][0]["bundle_id"] == "archive/20260412-cb-proof/cb-proof-test"


@patch("app.api.review_nrc_aps.compose_workbench_compare_targets")
def test_workbench_compare_targets_route_maps_invalid_bundle_to_400(mock_targets) -> None:
    mock_targets.side_effect = ValueError("candidate_b_bundle_id_invalid")

    response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_bundle_id": "../bad",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "candidate_b_bundle_id_invalid"


@patch("app.api.review_nrc_aps.compose_workbench_compare_targets")
def test_workbench_compare_targets_route_maps_invalid_baseline_run_to_400(mock_targets) -> None:
    mock_targets.side_effect = ValueError("invalid_baseline_run")

    response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_bundle_id": "archive/20260412-cb-proof/cb-proof-test",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_baseline_run"


@patch("app.api.review_nrc_aps.compose_workbench_compare_targets")
def test_workbench_compare_targets_route_returns_payload(mock_targets) -> None:
    mock_targets.return_value = _targets_payload()

    response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_bundle_id": "archive/20260412-cb-proof/cb-proof-test",
        },
    )

    assert response.status_code == 200
    assert response.json()["targets"][0]["fixture_id"] == "fixture-001"
    mock_targets.assert_called_once_with(
        baseline_run_id="baseline-run-001",
        candidate_a_run_id="candidate-a-run-001",
        candidate_b_source_kind="bundle",
        candidate_b_bundle_id="archive/20260412-cb-proof/cb-proof-test",
        candidate_b_run_id=None,
    )


@patch("app.api.review_nrc_aps.compose_workbench_compare_targets")
def test_workbench_compare_targets_route_accepts_candidate_b_runtime_source(mock_targets) -> None:
    mock_targets.return_value = NrcApsWorkbenchCompareTargetsOut(
        baseline_run_id="baseline-run-001",
        candidate_a_run_id="candidate-a-run-001",
        candidate_b_source_kind="runtime",
        candidate_b_run_id="candidate-b-runtime-001",
        default_fixture_id="fixture-001",
        targets=[
            NrcApsWorkbenchCompareTargetItemOut(
                fixture_id="fixture-001",
                display_label="Fixture 001",
                source_file_name="fixture-001.pdf",
                baseline_target_id="target-baseline-001",
                candidate_a_target_id="target-candidate-a-001",
                candidate_b_target_id="target-candidate-b-001",
            )
        ],
    )

    response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_source_kind": "runtime",
            "candidate_b_run_id": "candidate-b-runtime-001",
        },
    )

    assert response.status_code == 200
    assert response.json()["candidate_b_source_kind"] == "runtime"
    assert response.json()["candidate_b_run_id"] == "candidate-b-runtime-001"
    mock_targets.assert_called_once_with(
        baseline_run_id="baseline-run-001",
        candidate_a_run_id="candidate-a-run-001",
        candidate_b_source_kind="runtime",
        candidate_b_bundle_id=None,
        candidate_b_run_id="candidate-b-runtime-001",
    )


@patch("app.api.review_nrc_aps.compose_workbench_compare_manifest")
def test_workbench_compare_manifest_route_maps_fixture_not_comparable_to_404(mock_manifest) -> None:
    mock_manifest.side_effect = ValueError("fixture_id_not_comparable")

    response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets/fixture-001/manifest",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_bundle_id": "archive/20260412-cb-proof/cb-proof-test",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "fixture_id_not_comparable"


@patch("app.api.review_nrc_aps.compose_workbench_compare_manifest")
@patch("app.api.review_nrc_aps.compose_workbench_compare_tab")
def test_workbench_compare_manifest_and_tab_routes_return_payloads(mock_tab, mock_manifest) -> None:
    mock_manifest.return_value = _manifest_payload()
    mock_tab.return_value = _tab_payload()

    manifest_response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets/fixture-001/manifest",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_bundle_id": "archive/20260412-cb-proof/cb-proof-test",
        },
    )
    tab_response = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets/fixture-001/tabs/summary",
        params={
            "baseline_run_id": "baseline-run-001",
            "candidate_a_run_id": "candidate-a-run-001",
            "candidate_b_bundle_id": "archive/20260412-cb-proof/cb-proof-test",
        },
    )

    assert manifest_response.status_code == 200
    assert manifest_response.json()["source_identity"]["fixture_id"] == "fixture-001"
    assert manifest_response.json()["deep_links"]["candidate_b_trace"].startswith("/review/nrc-aps/candidate-b-trace?")
    assert tab_response.status_code == 200
    assert tab_response.json()["columns"]["candidate_b"]["warnings"] == ["footer_warning"]
    assert tab_response.json()["columns"]["candidate_b"]["deep_link"].startswith("/review/nrc-aps/candidate-b-trace?")
