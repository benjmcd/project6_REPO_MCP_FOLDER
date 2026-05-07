from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ApsContentDocument,
    ConnectorRun,
    ConnectorRunTarget,
    DatasetVersion,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3Descriptor,
    L3GateBIdempotencyKey,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementOutputPackage,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
    L3SignedReferenceAuditEvent,
    L3SignedReferenceReceipt,
    L3SignedReferenceRevocation,
    L3SignedReferenceToken,
    L3TypingRecord,
)
from test_layer3_api import client as client
from test_layer3_aps_handoff import _seed_aps_content_fixture
from test_layer3_pass_entry import _seed_timeseries_dataset_version


@dataclass(frozen=True)
class SeededSources:
    dataset_version_ids: tuple[str, str]
    aps_run_id: str
    aps_target_id: str
    aps_content_id: str


class Layer3ApiDriver:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def post_ok(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    def preflight(self) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/preflight",
            {
                "client_request_id": "bounded-e2e-preflight",
                "natural_language_intent": (
                    "Review two deterministic cohort dataset versions with an APS content companion."
                ),
                "manual_constraints": {"source_classes": ["dataset_version", "aps_content_document"]},
            },
        )

    def source_preview(self, *, preflight_id: str) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/source-preview",
            {
                "client_request_id": "bounded-e2e-source-preview",
                "preflight_id": preflight_id,
                "selected_source_classes": ["dataset_version", "aps_content_document"],
            },
        )

    def material_preview(
        self,
        *,
        preflight_id: str,
        source: dict[str, Any],
        seeded: SeededSources,
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/material-preview",
            {
                "client_request_id": "bounded-e2e-material-preview",
                "preflight_id": preflight_id,
                "source_set_id": source["source_set_id"],
                "source_candidate_ids": [
                    candidate["source_candidate_id"] for candidate in source["source_candidates"]
                ],
                "dataset_version_ids": list(seeded.dataset_version_ids),
                "aps_content_document_ids": [seeded.aps_content_id],
                "query_basis": {
                    "terms": ["bounded", "associated-cohort", "aps"],
                    "filters": {
                        "dataset_version_ids": list(seeded.dataset_version_ids),
                        "aps_content_document_ids": [seeded.aps_content_id],
                    },
                },
            },
        )

    def gate_b_decision(
        self,
        *,
        preflight_id: str,
        source_set_id: str,
        material: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/gate-b/decision",
            {
                "client_request_id": "bounded-e2e-gate-b",
                "preflight_id": preflight_id,
                "source_set_id": source_set_id,
                "material_preview_id": material["material_preview_id"],
                "material_preview_hash": material["material_preview_hash"],
                "candidate_decisions": [_approved_decision(candidate) for candidate in material["material_candidates"]],
            },
        )

    def gate_c_commit(self, *, session_id: str) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/gate-c/preview",
            {
                "client_request_id": "bounded-e2e-gate-c",
                "session_id": session_id,
                "commit_typing": True,
            },
        )


class Layer3StateAssertions:
    def __init__(self, client: TestClient, tmp_path: Path) -> None:
        self._client = client
        self._tmp_path = tmp_path

    def counts(self) -> dict[str, int]:
        with self._client.layer3_session_factory() as db:
            return {
                "analysis_artifacts": db.query(AnalysisArtifact).count(),
                "analysis_groups": db.query(L3AnalysisGroup).count(),
                "analysis_plans": db.query(L3AnalysisPlan).count(),
                "analysis_runs": db.query(AnalysisRun).count(),
                "analysis_sets": db.query(L3AnalysisSet).count(),
                "analysis_units": db.query(L3AnalysisUnit).count(),
                "aps_content_documents": db.query(ApsContentDocument).count(),
                "connector_run_targets": db.query(ConnectorRunTarget).count(),
                "connector_runs": db.query(ConnectorRun).count(),
                "dataset_versions": db.query(DatasetVersion).count(),
                "descriptors": db.query(L3Descriptor).count(),
                "gate_b_keys": db.query(L3GateBIdempotencyKey).count(),
                "material_snapshots": db.query(L3MaterialSnapshot).count(),
                "output_packages": db.query(L3OutputPackage).count(),
                "package_supersession_commits": db.query(L3PackageSupersessionCommit).count(),
                "pass_runs": db.query(L3PassRun).count(),
                "reconciliations": db.query(L3ReconciliationRecord).count(),
                "replacement_artifact_manifests": db.query(L3ReplacementPackageArtifactManifest).count(),
                "replacement_authorities": db.query(L3ReplacementPackageSetAuthority).count(),
                "replacement_packages": db.query(L3ReplacementOutputPackage).count(),
                "retrieval_events": db.query(L3RetrievalEvent).count(),
                "selection_manifests": db.query(L3SelectionManifest).count(),
                "sessions": db.query(L3Session).count(),
                "signed_reference_audit_events": db.query(L3SignedReferenceAuditEvent).count(),
                "signed_reference_receipts": db.query(L3SignedReferenceReceipt).count(),
                "signed_reference_revocations": db.query(L3SignedReferenceRevocation).count(),
                "signed_reference_tokens": db.query(L3SignedReferenceToken).count(),
                "typing_records": db.query(L3TypingRecord).count(),
            }

    def files(self) -> set[str]:
        return {str(path.relative_to(self._tmp_path)) for path in self._tmp_path.rglob("*") if path.is_file()}

    def assert_no_layer3_writes(self, before: dict[str, int]) -> None:
        after = self.counts()
        layer3_keys = [key for key in before if key not in {"dataset_versions", "aps_content_documents"}]
        assert {key: after[key] for key in layer3_keys} == {key: before[key] for key in layer3_keys}

    def assert_gate_b_state(self, *, session_id: str, seeded: SeededSources) -> None:
        with self._client.layer3_session_factory() as db:
            assert db.query(L3Session).filter(L3Session.session_id == session_id).count() == 1
            assert db.query(L3SelectionManifest).filter(L3SelectionManifest.session_id == session_id).count() == 1
            assert db.query(L3Descriptor).filter(L3Descriptor.session_id == session_id).count() == 3
            assert db.query(L3RetrievalEvent).filter(L3RetrievalEvent.session_id == session_id).count() == 3
            snapshots = (
                db.query(L3MaterialSnapshot)
                .filter(L3MaterialSnapshot.session_id == session_id)
                .order_by(L3MaterialSnapshot.source_shape.asc(), L3MaterialSnapshot.payload_ref.asc())
                .all()
            )
            assert [snapshot.source_shape for snapshot in snapshots].count("dataset_version") == 2
            assert [snapshot.source_shape for snapshot in snapshots].count("aps_content_document") == 1
            dataset_ids = [
                snapshot.source_identity_json["dataset_version_id"]
                for snapshot in snapshots
                if snapshot.source_shape == "dataset_version"
            ]
            assert sorted(dataset_ids) == sorted(seeded.dataset_version_ids)
            assert any(
                snapshot.source_identity_json.get("content_id") == seeded.aps_content_id
                for snapshot in snapshots
                if snapshot.source_shape == "aps_content_document"
            )
            for snapshot in snapshots:
                _assert_file_sha256(snapshot.payload_ref, snapshot.payload_hash)

    def assert_gate_c_current_api_boundary(self, *, session_id: str) -> None:
        with self._client.layer3_session_factory() as db:
            assert db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count() == 3
            assert db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).count() == 3
            assert db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).count() == 3
            sets = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).all()
            assert len(sets) == 3
            assert {analysis_set.set_type for analysis_set in sets} == {"single_item"}
            associated_sets = (
                db.query(L3AnalysisSet)
                .filter(L3AnalysisSet.session_id == session_id, L3AnalysisSet.set_type == "associated_cohort")
                .all()
            )
            assert associated_sets == []
            for analysis_set in sets:
                assert "requested_method_name" not in analysis_set.formation_basis_json

    def assert_forbidden_side_effects_absent(self, *, seeded_counts: dict[str, int]) -> None:
        counts = self.counts()
        assert counts["connector_runs"] == seeded_counts["connector_runs"]
        assert counts["connector_run_targets"] == seeded_counts["connector_run_targets"]
        assert counts["replacement_authorities"] == 0
        assert counts["replacement_packages"] == 0
        assert counts["replacement_artifact_manifests"] == 0
        assert counts["package_supersession_commits"] == 0
        assert counts["output_packages"] == 0
        assert counts["reconciliations"] == 0
        assert counts["analysis_artifacts"] == 0
        assert counts["analysis_runs"] == 0
        assert counts["signed_reference_tokens"] == 0
        assert counts["signed_reference_receipts"] == 0
        assert counts["signed_reference_revocations"] == 0
        assert counts["signed_reference_audit_events"] == 0


def test_layer3_bounded_e2e_api_associated_cohort_stops_at_current_typing_boundary(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_sources(client, tmp_path)
    driver = Layer3ApiDriver(client)
    state = Layer3StateAssertions(client, tmp_path)
    seeded_counts = state.counts()
    seeded_files = state.files()

    preflight = driver.preflight()
    _assert_forbidden_response_surface_absent(preflight)
    state.assert_no_layer3_writes(seeded_counts)
    assert state.files() == seeded_files

    source = driver.source_preview(preflight_id=preflight["preflight_id"])
    _assert_source_preview(source)
    _assert_forbidden_response_surface_absent(source)
    state.assert_no_layer3_writes(seeded_counts)
    assert state.files() == seeded_files

    material = driver.material_preview(preflight_id=preflight["preflight_id"], source=source, seeded=seeded)
    _assert_material_preview(material, seeded=seeded)
    _assert_forbidden_response_surface_absent(material)
    state.assert_no_layer3_writes(seeded_counts)
    assert state.files() == seeded_files

    gate_b = driver.gate_b_decision(
        preflight_id=preflight["preflight_id"],
        source_set_id=source["source_set_id"],
        material=material,
    )
    assert gate_b["status"] == "ok"
    session_id = gate_b["session_id"]
    state.assert_gate_b_state(session_id=session_id, seeded=seeded)
    state.assert_forbidden_side_effects_absent(seeded_counts=seeded_counts)

    gate_c = driver.gate_c_commit(session_id=session_id)
    assert gate_c["next_state"] == "plan_preview_ready"
    assert gate_c["authority_rail"]["typing_status"] == "committed"
    # Current API Gate B persists one descriptor per approved material candidate,
    # so Gate C has no co-retrieval authority to form an associated cohort.
    state.assert_gate_c_current_api_boundary(session_id=session_id)
    state.assert_forbidden_side_effects_absent(seeded_counts=seeded_counts)


def _seed_sources(client: TestClient, tmp_path: Path) -> SeededSources:
    seeded = SeededSources(
        dataset_version_ids=("dv-bounded-e2e-cohort-001", "dv-bounded-e2e-cohort-002"),
        aps_run_id="run-bounded-e2e-aps-001",
        aps_target_id="target-bounded-e2e-aps-001",
        aps_content_id="content-bounded-e2e-aps-001",
    )
    with client.layer3_session_factory() as db:
        _seed_timeseries_dataset_version(
            db,
            tmp_path,
            dataset_id="ds-bounded-e2e-cohort-001",
            dataset_version_id=seeded.dataset_version_ids[0],
            measure_name="cohort_value_a",
            values=[10 + index for index in range(24)],
        )
        _seed_timeseries_dataset_version(
            db,
            tmp_path,
            dataset_id="ds-bounded-e2e-cohort-002",
            dataset_version_id=seeded.dataset_version_ids[1],
            measure_name="cohort_value_b",
            values=[100 + (index * 3) for index in range(24)],
        )
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=seeded.aps_run_id,
            target_id=seeded.aps_target_id,
            content_id=seeded.aps_content_id,
        )
        db.commit()
    return seeded


def _approved_decision(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "decision": "approved",
        "decision_basis": {
            "source_ref": candidate["source_ref"],
            "query_basis": candidate["query_basis"],
            "provenance_ref": candidate["provenance_ref"],
            "source_identity": candidate["source_identity"],
            "source_provenance": candidate["source_provenance"],
            "payload": candidate["payload"],
            "load_summary": candidate["load_summary"],
        },
    }


def _assert_source_preview(source: dict[str, Any]) -> None:
    assert {candidate["source_class"] for candidate in source["source_candidates"]} == {
        "dataset_version",
        "aps_content_document",
    }
    assert source["unsupported_sources"] == []


def _assert_material_preview(material: dict[str, Any], *, seeded: SeededSources) -> None:
    candidates = material["material_candidates"]
    assert len(candidates) == 3
    assert [candidate["source_class"] for candidate in candidates].count("dataset_version") == 2
    assert [candidate["source_class"] for candidate in candidates].count("aps_content_document") == 1
    assert sorted(
        candidate["source_identity"]["dataset_version_id"]
        for candidate in candidates
        if candidate["source_class"] == "dataset_version"
    ) == sorted(seeded.dataset_version_ids)
    assert any(
        candidate["source_identity"].get("content_id") == seeded.aps_content_id
        for candidate in candidates
        if candidate["source_class"] == "aps_content_document"
    )


def _assert_forbidden_response_surface_absent(payload: Any) -> None:
    forbidden_keys = {
        "artifact_manifest",
        "browser_state",
        "connector_run_id",
        "destination",
        "download_url",
        "external_target",
        "full_mockup",
        "llm_plan",
        "local_directory",
        "local_upload",
        "package_mutation",
        "provider_public_url",
        "public_url",
        "rag_plan",
        "signed_url",
        "vector_query",
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in forbidden_keys
            _assert_forbidden_response_surface_absent(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_forbidden_response_surface_absent(value)


def _assert_file_sha256(path: str, expected_hash: str) -> None:
    artifact = Path(path)
    assert artifact.exists()
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == expected_hash
