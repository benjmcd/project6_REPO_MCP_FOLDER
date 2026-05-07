from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
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
from app.services import dataframe_io
from app.services.layer3_raw_mixed_bridge import (
    RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_SEED_MODE,
    RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID,
)
from app.services.layer3_qual_aps_execution import (
    ENGINE_FAMILY_QUAL_APS_DOCUMENT,
    PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
    QUAL_APS_METHOD_NAME,
    QUAL_APS_OUTPUT_SCHEMA_ID,
    QUAL_APS_SOURCE_GATE,
)
from test_layer3_api import (
    _aps_handoff_dispatch_payload,
    _external_export_download_deliver_payload,
    _external_export_download_prepare_payload,
    _handoff_export_prepare_payload,
    client as client,
)
from test_layer3_aps_handoff import _seed_aps_content_fixture
from test_layer3_pass_entry import _seed_timeseries_dataset_version


@dataclass(frozen=True)
class SeededSources:
    dataset_version_ids: tuple[str, str]
    aps_run_id: str
    aps_target_id: str
    aps_content_id: str


@dataclass(frozen=True)
class SeededApsDocument:
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

    def post_blocked(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=payload)
        assert response.status_code == 409, response.text
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

    def aps_doc_preflight(self) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/preflight",
            {
                "client_request_id": "aps-qual-e2e-preflight",
                "natural_language_intent": "Review one indexed APS content document as qualitative source material.",
                "manual_constraints": {"source_classes": ["aps_content_document"]},
            },
        )

    def aps_doc_source_preview(self, *, preflight_id: str) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/source-preview",
            {
                "client_request_id": "aps-qual-e2e-source-preview",
                "preflight_id": preflight_id,
                "selected_source_classes": ["aps_content_document"],
            },
        )

    def aps_doc_material_preview(
        self,
        *,
        preflight_id: str,
        source: dict[str, Any],
        seeded: SeededApsDocument,
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/material-preview",
            {
                "client_request_id": "aps-qual-e2e-material-preview",
                "preflight_id": preflight_id,
                "source_set_id": source["source_set_id"],
                "source_candidate_ids": [
                    candidate["source_candidate_id"] for candidate in source["source_candidates"]
                ],
                "aps_content_document_ids": [seeded.aps_content_id],
                "query_basis": {
                    "terms": ["aps", "qualitative", "single-document"],
                    "filters": {"aps_content_document_ids": [seeded.aps_content_id]},
                },
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
                "candidate_decisions": [_gate_b_decision(candidate) for candidate in material["material_candidates"]],
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

    def plan_preview(self, *, session_id: str) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/plan/preview",
            {
                "client_request_id": "bounded-e2e-plan-preview",
                "session_id": session_id,
                "include_exclusions": True,
                "preview_scope": "owner_service_default",
            },
        )

    def plan_approve(self, *, session_id: str, preview: dict[str, Any]) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/plan/approve",
            {
                "client_request_id": "bounded-e2e-plan-approve",
                "session_id": session_id,
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "operator_confirmation": True,
                "approval_scope": "owner_service_default",
            },
        )

    def execution_select(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/execution/select",
            {
                "client_request_id": "bounded-e2e-execution-select",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
            },
        )

    def execution_start(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/execution/start",
            {
                "client_request_id": "bounded-e2e-execution-start",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
            },
        )

    def execution_status(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/execution/result/status",
            {
                "client_request_id": "bounded-e2e-execution-status",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "operator_view_mode": "status_only",
            },
        )

    def execution_review(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        status: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/execution/result/review",
            {
                "client_request_id": "bounded-e2e-execution-review",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "operator_decision": "approved",
                "review_notes": "Bounded cohort output is traceable for package construction.",
                "reviewed_output_items": [
                    {
                        "item_ref": "bounded-cohort-output",
                        "item_type": "finding",
                        "trace": {
                            "session_id": session_id,
                            "analysis_plan_id": approval["analysis_plan_id"],
                            "pass_run_id": selection["pass_run_ids"][0],
                            "analysis_run_id": start["analysis_run_id"],
                            "output_payload_ref": status["output_payload_ref"],
                        },
                    }
                ],
            },
        )

    def package_preview(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/package/review/preview",
            {
                "client_request_id": "bounded-e2e-package-preview",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "result_review_record_ref": review["review_record_ref"],
            },
        )

    def qualitative_package_preview(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/package/review/preview",
            {
                "client_request_id": "aps-qual-e2e-package-preview",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "result_review_record_ref": review["review_record_ref"],
            },
        )

    def qualitative_package_commit(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        package_preview: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/package/review/commit",
            {
                "client_request_id": "aps-qual-e2e-package-commit",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
            },
        )

    def qualitative_package_submit(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        commit: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/package/review/submit",
            {
                "client_request_id": "aps-qual-e2e-package-submit",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": commit["package_review_preview_hash"],
                "construction_basis_hash": commit["construction_basis_hash"],
                "reconciliation_record_id": commit["reconciliation_record_id"],
                "output_package_ids": commit["output_package_ids"],
                "payload_refs": commit["payload_refs"],
                "payload_hashes": commit["payload_hashes"],
                "operator_decision": "approved",
                "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
            },
        )

    def package_commit(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        package_preview: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/package/review/commit",
            {
                "client_request_id": "bounded-e2e-package-commit",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
            },
        )

    def package_submit(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        commit: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/package/review/submit",
            {
                "client_request_id": "bounded-e2e-package-submit",
                "session_id": session_id,
                "analysis_plan_id": approval["analysis_plan_id"],
                "pass_run_id": selection["pass_run_ids"][0],
                "preview_id": preview["preview_id"],
                "preview_hash": preview["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "result_review_record_ref": review["review_record_ref"],
                "package_review_preview_hash": commit["package_review_preview_hash"],
                "reconciliation_record_id": commit["reconciliation_record_id"],
                "output_package_ids": [package["output_package_id"] for package in commit["output_packages"]],
                "payload_hashes": commit["payload_hashes"],
                "operator_decision": "approved",
                "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
            },
        )

    def handoff_prepare(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        commit: dict[str, Any],
        submit: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/handoff/export/prepare",
            _handoff_export_prepare_payload(
                request_id="bounded-e2e-handoff-prepare",
                session_id=session_id,
                preview_body=preview,
                approval_body=approval,
                selection_body=selection,
                start_body=start,
                review_body=review,
                commit_body=commit,
                submit_body=submit,
            ),
        )

    def aps_dispatch(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        commit: dict[str, Any],
        submit: dict[str, Any],
        prepare: dict[str, Any],
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/handoff/aps/dispatch",
            _aps_handoff_dispatch_payload(
                request_id="bounded-e2e-aps-dispatch",
                session_id=session_id,
                preview_body=preview,
                approval_body=approval,
                selection_body=selection,
                start_body=start,
                review_body=review,
                commit_body=commit,
                submit_body=submit,
                prepare_body=prepare,
            ),
        )

    def external_export_download_prepare(
        self,
        *,
        session_id: str,
        preview: dict[str, Any],
        approval: dict[str, Any],
        selection: dict[str, Any],
        start: dict[str, Any],
        review: dict[str, Any],
        commit: dict[str, Any],
        submit: dict[str, Any],
        prepare: dict[str, Any],
        dispatch: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = _external_export_download_prepare_payload(
            request_id="bounded-e2e-download-prepare",
            session_id=session_id,
            preview_body=preview,
            approval_body=approval,
            selection_body=selection,
            start_body=start,
            review_body=review,
            commit_body=commit,
            submit_body=submit,
            prepare_body=prepare,
            dispatch_body=dispatch,
        )
        return payload, self.post_ok("/api/v1/layer3/handoff/export/download/prepare", payload)

    def external_export_download_deliver(
        self,
        *,
        prepare_payload: dict[str, Any],
        readiness: dict[str, Any],
    ) -> Any:
        response = self._client.post(
            "/api/v1/layer3/handoff/export/download/deliver",
            json=_external_export_download_deliver_payload(
                request_id="bounded-e2e-download-deliver",
                prepare_payload=prepare_payload,
                readiness_body=readiness,
            ),
        )
        assert response.status_code == 200, response.text
        return response

    def raw_mixed_seed(
        self,
        *,
        seeded: SeededSources,
        manifest_ref: str,
        manifest_hash: str,
    ) -> dict[str, Any]:
        return self.post_ok(
            "/api/v1/layer3/source/mixed-corpus/seed",
            {
                "schema_id": "layer3.raw_mixed_corpus_seed_request.v1",
                "schema_version": 1,
                "client_request_id": "bounded-e2e-raw-mixed-seed",
                "seed_mode": RAW_MIXED_CORPUS_SEED_MODE,
                "corpus_batch_id": "batch-bounded-e2e-raw-mixed-001",
                "aps_run_id": seeded.aps_run_id,
                "target_ids": [seeded.aps_target_id],
                "artifact_manifest_ref": manifest_ref,
                "artifact_manifest_hash": manifest_hash,
                "requested_source_classes": ["dataset_version", "aps_content_document"],
                "operator_confirmation": True,
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
                "aps_content_chunks": db.query(ApsContentChunk).count(),
                "aps_content_documents": db.query(ApsContentDocument).count(),
                "aps_content_linkages": db.query(ApsContentLinkage).count(),
                "connector_run_targets": db.query(ConnectorRunTarget).count(),
                "connector_runs": db.query(ConnectorRun).count(),
                "datasets": db.query(Dataset).count(),
                "dataset_source_provenance": db.query(DatasetSourceProvenance).count(),
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

    def relative_file(self, path: str) -> str:
        return str(Path(path).relative_to(self._tmp_path))

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
            aps_snapshot = next(snapshot for snapshot in snapshots if snapshot.source_shape == "aps_content_document")
            assert aps_snapshot.source_identity_json["content_id"] == seeded.aps_content_id
            assert aps_snapshot.source_identity_json["run_id"] == seeded.aps_run_id
            assert aps_snapshot.source_identity_json["target_id"] == seeded.aps_target_id
            assert (
                aps_snapshot.source_provenance_json["analysis_admission_role"]
                == "aps_handoff_companion_provenance"
            )
            dataset_group_ids = {
                snapshot.co_retrieval_group_id
                for snapshot in snapshots
                if snapshot.source_shape == "dataset_version"
            }
            aps_group_ids = {
                snapshot.co_retrieval_group_id
                for snapshot in snapshots
                if snapshot.source_shape == "aps_content_document"
            }
            assert len(dataset_group_ids) == 1
            assert None not in dataset_group_ids
            assert not dataset_group_ids.intersection(aps_group_ids)
            for snapshot in snapshots:
                _assert_file_sha256(snapshot.payload_ref, snapshot.payload_hash)

    def assert_gate_c_associated_cohort_boundary(self, *, session_id: str) -> None:
        with self._client.layer3_session_factory() as db:
            assert db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count() == 3
            assert db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).count() == 3
            assert db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).count() == 2
            sets = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).all()
            assert len(sets) == 2
            assert {analysis_set.set_type for analysis_set in sets} == {"associated_cohort", "single_item"}
            associated_set = (
                db.query(L3AnalysisSet)
                .filter(L3AnalysisSet.session_id == session_id, L3AnalysisSet.set_type == "associated_cohort")
                .one()
            )
            assert len(associated_set.analysis_unit_ids_json) == 2
            assert associated_set.formation_basis_json["group_basis"] == "same_co_retrieval_group"
            assert associated_set.formation_basis_json["analysis_modality"] == "quantitative"
            assert associated_set.formation_basis_json["requested_method_name"] == "descriptive_summary"
            companion_set = (
                db.query(L3AnalysisSet)
                .filter(L3AnalysisSet.session_id == session_id, L3AnalysisSet.set_type == "single_item")
                .one()
            )
            companion_unit = db.get(L3AnalysisUnit, companion_set.analysis_unit_ids_json[0])
            assert companion_unit.analysis_modality == "qualitative"
            companion_snapshot = db.get(L3MaterialSnapshot, companion_unit.member_snapshot_ids_json[0])
            assert companion_snapshot.source_shape == "aps_content_document"
            assert (
                companion_snapshot.source_provenance_json["analysis_admission_role"]
                == "aps_handoff_companion_provenance"
            )

    def assert_gate_b_aps_document_state(self, *, session_id: str, seeded: SeededApsDocument) -> None:
        with self._client.layer3_session_factory() as db:
            assert db.query(L3Session).filter(L3Session.session_id == session_id).count() == 1
            assert db.query(L3SelectionManifest).filter(L3SelectionManifest.session_id == session_id).count() == 1
            assert db.query(L3Descriptor).filter(L3Descriptor.session_id == session_id).count() == 1
            assert db.query(L3RetrievalEvent).filter(L3RetrievalEvent.session_id == session_id).count() == 1
            snapshot = db.query(L3MaterialSnapshot).filter(L3MaterialSnapshot.session_id == session_id).one()
            assert snapshot.source_shape == "aps_content_document"
            assert snapshot.source_identity_json["content_id"] == seeded.aps_content_id
            assert snapshot.source_identity_json["run_id"] == seeded.aps_run_id
            assert snapshot.source_identity_json["target_id"] == seeded.aps_target_id
            assert "dataset_version_id" not in snapshot.source_identity_json
            assert snapshot.source_provenance_json["source_family"] == "aps_content_document"
            assert snapshot.source_provenance_json["source_admission_state"] == "admitted_content_document"
            assert "analysis_admission_role" not in snapshot.source_provenance_json
            _assert_file_sha256(snapshot.payload_ref, snapshot.payload_hash)

    def assert_gate_c_single_aps_document_boundary(self, *, session_id: str, seeded: SeededApsDocument) -> None:
        with self._client.layer3_session_factory() as db:
            assert db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count() == 1
            assert db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).count() == 1
            assert db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).count() == 1
            analysis_set = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).one()
            assert analysis_set.set_type == "single_item"
            assert analysis_set.formation_basis_json["analysis_modality"] == "qualitative"
            analysis_unit = db.get(L3AnalysisUnit, analysis_set.analysis_unit_ids_json[0])
            assert analysis_unit.analysis_modality == "qualitative"
            snapshot = db.get(L3MaterialSnapshot, analysis_unit.member_snapshot_ids_json[0])
            assert snapshot.source_shape == "aps_content_document"
            assert snapshot.source_identity_json["content_id"] == seeded.aps_content_id

    def assert_approved_plan_method_authority(self, *, session_id: str, seeded: SeededSources) -> None:
        with self._client.layer3_session_factory() as db:
            plan = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).one()
            planned_pass = plan.plan_json["planned_passes_json"][0]
            assert planned_pass["selected_method_name"] == "descriptive_summary"
            assert planned_pass["requested_method_name"] == "descriptive_summary"
            assert planned_pass["requested_method_source"] == "analysis_set.formation_basis_json.requested_method_name"
            assert planned_pass["source_gate"] == "78_COHORT_FREEZE"
            assert sorted(planned_pass["source_dataset_version_ids_json"]) == sorted(seeded.dataset_version_ids)

    def assert_approved_aps_document_plan_authority(self, *, session_id: str) -> None:
        with self._client.layer3_session_factory() as db:
            plan = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).one()
            planned_pass = plan.plan_json["planned_passes_json"][0]
            assert planned_pass["pass_type"] == "single_item"
            assert planned_pass["pass_scope"] == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
            assert planned_pass["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
            assert planned_pass["selected_method_name"] == QUAL_APS_METHOD_NAME
            assert planned_pass["source_gate"] == QUAL_APS_SOURCE_GATE
            assert "source_dataset_version_ids_json" not in planned_pass

    def assert_forbidden_side_effects_absent(
        self,
        *,
        seeded_counts: dict[str, int],
        allowed_output_packages: int = 0,
        allowed_reconciliations: int = 0,
    ) -> None:
        counts = self.counts()
        assert counts["connector_runs"] == seeded_counts["connector_runs"]
        assert counts["connector_run_targets"] == seeded_counts["connector_run_targets"]
        assert counts["replacement_authorities"] == 0
        assert counts["replacement_packages"] == 0
        assert counts["replacement_artifact_manifests"] == 0
        assert counts["package_supersession_commits"] == 0
        assert counts["output_packages"] == allowed_output_packages
        assert counts["reconciliations"] == allowed_reconciliations
        assert counts["analysis_artifacts"] == 0
        assert counts["analysis_runs"] == 0
        assert counts["signed_reference_tokens"] == 0
        assert counts["signed_reference_receipts"] == 0
        assert counts["signed_reference_revocations"] == 0
        assert counts["signed_reference_audit_events"] == 0


def test_layer3_bounded_e2e_api_associated_cohort_reaches_download_delivery(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_cohort_dataframe_persistence(monkeypatch, tmp_path)
    seeded = _seed_sources(client, tmp_path)
    driver = Layer3ApiDriver(client)
    state = Layer3StateAssertions(client, tmp_path)
    seeded_counts = state.counts()
    seeded_files = state.files()

    _drive_bounded_e2e_api_associated_cohort_to_download_delivery(
        driver=driver,
        state=state,
        seeded=seeded,
        seeded_counts=seeded_counts,
        seeded_files=seeded_files,
    )


def test_layer3_raw_mixed_seed_bridge_drives_bounded_e2e_path(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_cohort_dataframe_persistence(monkeypatch, tmp_path)
    seeded_authority = _seed_sources(client, tmp_path)
    driver = Layer3ApiDriver(client)
    state = Layer3StateAssertions(client, tmp_path)
    manifest_ref, manifest_hash = _write_raw_mixed_seed_manifest(seeded_authority)
    seeded_counts = state.counts()
    seeded_files = state.files()

    seed = driver.raw_mixed_seed(
        seeded=seeded_authority,
        manifest_ref=manifest_ref,
        manifest_hash=manifest_hash,
    )

    assert seed["schema_id"] == RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID
    assert seed["seed_mode"] == RAW_MIXED_CORPUS_SEED_MODE
    assert seed["source_seed_state"] == "seeded"
    assert seed["source_classes"] == ["dataset_version", "aps_content_document"]
    assert seed["layer3_flow_started"] is False
    assert seed["next_allowed_actions"] == ["run_layer3_preflight_with_seeded_source_ids"]
    assert state.counts() == seeded_counts
    assert state.files() == seeded_files
    _assert_forbidden_response_surface_absent(seed)

    bridge_sources = _seeded_sources_from_raw_mixed_seed_response(client, seed)
    _drive_bounded_e2e_api_associated_cohort_to_download_delivery(
        driver=driver,
        state=state,
        seeded=bridge_sources,
        seeded_counts=seeded_counts,
        seeded_files=seeded_files,
    )


def test_layer3_standalone_aps_content_document_qualitative_e2e_reaches_read_only_package_preview(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_aps_document_source(client, tmp_path)
    driver = Layer3ApiDriver(client)
    state = Layer3StateAssertions(client, tmp_path)
    seeded_counts = state.counts()
    seeded_files = state.files()

    _drive_standalone_aps_document_qualitative_e2e_to_read_only_package_preview(
        driver=driver,
        state=state,
        seeded=seeded,
        seeded_counts=seeded_counts,
        seeded_files=seeded_files,
    )


def _drive_bounded_e2e_api_associated_cohort_to_download_delivery(
    *,
    driver: Layer3ApiDriver,
    state: Layer3StateAssertions,
    seeded: SeededSources,
    seeded_counts: dict[str, int],
    seeded_files: set[str],
) -> None:
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
    assert len(gate_b["approved_candidate_ids"]) == 3
    assert gate_b["flagged_candidate_ids"] == []
    session_id = gate_b["session_id"]
    state.assert_gate_b_state(session_id=session_id, seeded=seeded)
    state.assert_forbidden_side_effects_absent(seeded_counts=seeded_counts)

    gate_c = driver.gate_c_commit(session_id=session_id)
    assert gate_c["next_state"] == "plan_preview_ready"
    assert gate_c["authority_rail"]["typing_status"] == "committed"
    state.assert_gate_c_associated_cohort_boundary(session_id=session_id)
    state.assert_forbidden_side_effects_absent(seeded_counts=seeded_counts)

    gate_c_counts = state.counts()
    plan_preview = driver.plan_preview(session_id=session_id)
    _assert_descriptive_cohort_plan_preview(plan_preview, seeded=seeded)
    assert state.counts() == gate_c_counts

    plan_approval = driver.plan_approve(session_id=session_id, preview=plan_preview)
    assert plan_approval["next_state"] == "plan_approved"
    approval_counts = state.counts()
    assert approval_counts == {**gate_c_counts, "analysis_plans": gate_c_counts["analysis_plans"] + 1}
    state.assert_approved_plan_method_authority(session_id=session_id, seeded=seeded)

    selection = driver.execution_select(session_id=session_id, preview=plan_preview, approval=plan_approval)
    assert selection["status"] == "selected_not_started"
    selection_counts = state.counts()
    assert selection_counts == {**approval_counts, "pass_runs": approval_counts["pass_runs"] + 1}

    start = driver.execution_start(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
    )
    assert start["status"] in {"completed", "completed_with_warnings"}
    assert start["selected_method_name"] == "descriptive_summary"
    _assert_response_refs_exist(start)
    start_counts = state.counts()
    assert start_counts["analysis_runs"] == selection_counts["analysis_runs"] + 1
    assert start_counts["dataset_versions"] == selection_counts["dataset_versions"] + 1
    assert start_counts["pass_runs"] == selection_counts["pass_runs"]
    assert start_counts["output_packages"] == 0

    status = driver.execution_status(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
    )
    assert status["status"] == "available"
    assert status["selected_method_name"] == "descriptive_summary"
    _assert_response_refs_exist(status)
    assert state.counts() == start_counts

    review = driver.execution_review(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        status=status,
    )
    assert review["review_state"] == "execution_result_review_approved"
    assert state.counts() == start_counts

    package_preview = driver.package_preview(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
    )
    assert package_preview["pass_type"] == "associated_cohort"
    assert package_preview["selected_method_name"] == "descriptive_summary"
    assert state.counts() == start_counts

    package_commit = driver.package_commit(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        package_preview=package_preview,
    )
    assert package_commit["status"] == "committed"
    _assert_response_refs_exist(package_commit)
    commit_counts = state.counts()
    assert commit_counts == {
        **start_counts,
        "output_packages": start_counts["output_packages"] + 3,
        "reconciliations": start_counts["reconciliations"] + 1,
    }

    package_submit = driver.package_submit(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        commit=package_commit,
    )
    assert package_submit["package_review_state"] == "package_review_approved"
    assert state.counts() == commit_counts

    handoff_prepare = driver.handoff_prepare(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        commit=package_commit,
        submit=package_submit,
    )
    assert handoff_prepare["handoff_export_state"] == "handoff_export_prepared"
    _assert_response_refs_exist(handoff_prepare)
    assert state.counts() == commit_counts

    dispatch_counts_before = state.counts()
    files_before_dispatch = state.files()
    aps_dispatch = driver.aps_dispatch(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        commit=package_commit,
        submit=package_submit,
        prepare=handoff_prepare,
    )
    assert aps_dispatch["status"] == "dispatched"
    assert aps_dispatch["aps_handoff_state"] == "aps_handoff_dispatched"
    assert aps_dispatch["pass_type"] == "associated_cohort"
    assert sorted(aps_dispatch["source_dataset_version_ids"]) == sorted(seeded.dataset_version_ids)
    _assert_response_refs_exist(aps_dispatch)
    dispatch_counts = state.counts()
    assert dispatch_counts == {
        **dispatch_counts_before,
        "output_packages": dispatch_counts_before["output_packages"] + 1,
    }
    added_dispatch_files = state.files() - files_before_dispatch
    assert len(added_dispatch_files) == 1

    download_prepare_payload, download_prepare = driver.external_export_download_prepare(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        commit=package_commit,
        submit=package_submit,
        prepare=handoff_prepare,
        dispatch=aps_dispatch,
    )
    assert download_prepare["status"] == "prepared"
    assert download_prepare["external_export_download_state"] == "external_export_download_prepared"
    assert download_prepare["source_artifact_ref"] == aps_dispatch["aps_bundle_ref"]
    assert state.counts() == dispatch_counts
    assert state.files() == files_before_dispatch | added_dispatch_files

    delivery = driver.external_export_download_deliver(
        prepare_payload=download_prepare_payload,
        readiness=download_prepare,
    )
    assert delivery.headers["x-layer3-delivery-state"] == "external_export_download_delivered"
    assert delivery.headers["x-layer3-schema-id"] == "layer3.external_export_download_delivery.v1"
    assert delivery.content == Path(aps_dispatch["aps_bundle_ref"]).read_bytes()
    assert state.counts() == dispatch_counts
    assert state.files() == files_before_dispatch | added_dispatch_files


def _drive_standalone_aps_document_qualitative_e2e_to_read_only_package_preview(
    *,
    driver: Layer3ApiDriver,
    state: Layer3StateAssertions,
    seeded: SeededApsDocument,
    seeded_counts: dict[str, int],
    seeded_files: set[str],
) -> None:
    preflight = driver.aps_doc_preflight()
    _assert_forbidden_response_surface_absent(preflight)
    state.assert_no_layer3_writes(seeded_counts)
    assert state.files() == seeded_files

    source = driver.aps_doc_source_preview(preflight_id=preflight["preflight_id"])
    _assert_aps_doc_source_preview(source)
    _assert_forbidden_response_surface_absent(source)
    state.assert_no_layer3_writes(seeded_counts)
    assert state.files() == seeded_files

    material = driver.aps_doc_material_preview(
        preflight_id=preflight["preflight_id"],
        source=source,
        seeded=seeded,
    )
    _assert_aps_doc_material_preview(material, seeded=seeded)
    _assert_forbidden_response_surface_absent(material)
    state.assert_no_layer3_writes(seeded_counts)
    assert state.files() == seeded_files

    gate_b = driver.gate_b_decision(
        preflight_id=preflight["preflight_id"],
        source_set_id=source["source_set_id"],
        material=material,
    )
    assert gate_b["status"] == "ok"
    assert len(gate_b["approved_candidate_ids"]) == 1
    assert gate_b["flagged_candidate_ids"] == []
    session_id = gate_b["session_id"]
    state.assert_gate_b_aps_document_state(session_id=session_id, seeded=seeded)
    state.assert_forbidden_side_effects_absent(seeded_counts=seeded_counts)
    gate_b_files = state.files()
    assert len(gate_b_files - seeded_files) == 1

    gate_c = driver.gate_c_commit(session_id=session_id)
    assert gate_c["next_state"] == "plan_preview_ready"
    assert gate_c["authority_rail"]["typing_status"] == "committed"
    state.assert_gate_c_single_aps_document_boundary(session_id=session_id, seeded=seeded)
    state.assert_forbidden_side_effects_absent(seeded_counts=seeded_counts)
    assert state.files() == gate_b_files

    gate_c_counts = state.counts()
    plan_preview = driver.plan_preview(session_id=session_id)
    _assert_single_aps_doc_qualitative_plan_preview(plan_preview)
    assert state.counts() == gate_c_counts
    assert state.files() == gate_b_files

    plan_approval = driver.plan_approve(session_id=session_id, preview=plan_preview)
    assert plan_approval["next_state"] == "plan_approved"
    approval_counts = state.counts()
    assert approval_counts == {**gate_c_counts, "analysis_plans": gate_c_counts["analysis_plans"] + 1}
    state.assert_approved_aps_document_plan_authority(session_id=session_id)

    selection = driver.execution_select(session_id=session_id, preview=plan_preview, approval=plan_approval)
    assert selection["status"] == "selected_not_started"
    selection_counts = state.counts()
    assert selection_counts == {**approval_counts, "pass_runs": approval_counts["pass_runs"] + 1}
    assert state.files() == gate_b_files

    start = driver.execution_start(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
    )
    assert start["status"] == "completed"
    assert start["analysis_run_id"] is None
    assert start["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert start["selected_method_name"] == QUAL_APS_METHOD_NAME
    assert start["dataset_version_id"] is None
    _assert_response_refs_exist(start)
    output = _assert_single_aps_doc_qualitative_output(start, seeded=seeded)
    start_counts = state.counts()
    assert start_counts == selection_counts
    execution_files = state.files()
    assert execution_files == gate_b_files | {state.relative_file(start["output_payload_ref"])}

    status = driver.execution_status(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
    )
    assert status["status"] == "available"
    assert status["analysis_run_id"] is None
    assert status["output_metadata_summary"]["content_id"] == seeded.aps_content_id
    assert status["output_metadata_summary"]["chunk_ids"] == output["chunk_summary"]["chunk_ids"]
    _assert_response_refs_exist(status)
    assert state.counts() == start_counts
    assert state.files() == execution_files

    review = driver.execution_review(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        status=status,
    )
    assert review["review_state"] == "execution_result_review_approved"
    assert state.counts() == start_counts
    assert state.files() == execution_files

    package_preview = driver.qualitative_package_preview(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
    )
    _assert_single_aps_doc_qualitative_package_preview(
        package_preview,
        output=output,
        seeded=seeded,
        start=start,
    )
    assert state.counts() == start_counts
    assert state.files() == execution_files

    package_commit = driver.qualitative_package_commit(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        package_preview=package_preview,
    )
    _assert_single_aps_doc_qualitative_package_commit(
        package_commit,
        package_preview=package_preview,
        output=output,
        seeded=seeded,
    )
    commit_counts = state.counts()
    assert commit_counts == {
        **start_counts,
        "output_packages": start_counts["output_packages"] + 3,
        "reconciliations": start_counts["reconciliations"] + 1,
    }
    package_files = state.files()
    assert len(package_files - execution_files) == 3
    state.assert_forbidden_side_effects_absent(
        seeded_counts=seeded_counts,
        allowed_output_packages=3,
        allowed_reconciliations=1,
    )

    package_submit = driver.qualitative_package_submit(
        session_id=session_id,
        preview=plan_preview,
        approval=plan_approval,
        selection=selection,
        start=start,
        review=review,
        commit=package_commit,
    )
    assert package_submit["schema_id"] == "layer3.qual_aps_package_review_submit.v1"
    assert package_submit["status"] == "submitted"
    assert package_submit["analysis_run_id"] is None
    assert package_submit["construction_basis_hash"] == package_commit["construction_basis_hash"]
    assert package_submit["payload_refs"] == package_commit["payload_refs"]
    assert package_submit["payload_hashes"] == package_commit["payload_hashes"]
    assert package_submit["package_review_state"] == "package_review_approved"
    assert package_submit["package_review_submit_enabled"] is False
    assert package_submit["handoff_enabled"] is False
    assert package_submit["aps_handoff_enabled"] is False
    assert package_submit["external_export_download_enabled"] is False
    assert package_submit["connector_dispatch_enabled"] is False
    assert package_submit["provider_public_url_enabled"] is False
    assert "package_review_submit" not in package_submit["downstream_unavailable"]
    assert "handoff" in package_submit["downstream_unavailable"]
    assert "external_export_download" in package_submit["downstream_unavailable"]
    assert state.counts() == commit_counts
    assert state.files() == package_files
    state.assert_forbidden_side_effects_absent(
        seeded_counts=seeded_counts,
        allowed_output_packages=3,
        allowed_reconciliations=1,
    )


def _write_raw_mixed_seed_manifest(seeded: SeededSources) -> tuple[str, str]:
    manifest_ref = "raw-mixed/bounded-e2e-raw-mixed-seed.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": "batch-bounded-e2e-raw-mixed-001",
        "aps_run_id": seeded.aps_run_id,
        "target_ids": [seeded.aps_target_id],
        "source_classes": ["dataset_version", "aps_content_document"],
        "dataset_version_ids": list(seeded.dataset_version_ids),
        "aps_content_document_ids": [seeded.aps_content_id],
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return manifest_ref, hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def _seeded_sources_from_raw_mixed_seed_response(client: TestClient, seed: dict[str, Any]) -> SeededSources:
    dataset_version_ids = tuple(seed["dataset_version_ids"])
    aps_content_document_ids = seed["aps_content_document_ids"]
    assert len(dataset_version_ids) == 2
    assert len(aps_content_document_ids) == 1
    aps_content_id = aps_content_document_ids[0]
    with client.layer3_session_factory() as db:
        linkage = db.query(ApsContentLinkage).filter(ApsContentLinkage.content_id == aps_content_id).one()
        return SeededSources(
            dataset_version_ids=(dataset_version_ids[0], dataset_version_ids[1]),
            aps_run_id=linkage.run_id,
            aps_target_id=linkage.target_id,
            aps_content_id=aps_content_id,
        )


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
        for dataset_version_id in seeded.dataset_version_ids:
            db.add(
                DatasetSourceProvenance(
                    dataset_source_provenance_id=f"prov-{dataset_version_id}",
                    dataset_version_id=dataset_version_id,
                    connector_run_id=seeded.aps_run_id,
                    source_system="nrc_adams_aps",
                    source_mode="bounded_e2e_raw_mixed_seed_fixture",
                    source_artifact_key=f"aps://{seeded.aps_run_id}/{seeded.aps_target_id}/{dataset_version_id}",
                    artifact_surface="dataset_version",
                    artifact_locator_type="server_owned_ref",
                    downloaded_sha256=hashlib.sha256(dataset_version_id.encode("utf-8")).hexdigest(),
                    raw_storage_ref=f"dataset_version:{dataset_version_id}",
                    source_reference_json={
                        "parser_family": "csv_table",
                        "target_id": seeded.aps_target_id,
                        "content_id": seeded.aps_content_id,
                    },
                    fetch_policy_mode="seed_fixture",
                )
            )
        db.commit()
    return seeded


def _seed_aps_document_source(client: TestClient, tmp_path: Path) -> SeededApsDocument:
    seeded = SeededApsDocument(
        aps_run_id="run-standalone-aps-qual-e2e-001",
        aps_target_id="target-standalone-aps-qual-e2e-001",
        aps_content_id="content-standalone-aps-qual-e2e-001",
    )
    with client.layer3_session_factory() as db:
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=seeded.aps_run_id,
            target_id=seeded.aps_target_id,
            content_id=seeded.aps_content_id,
        )
        db.commit()
    return seeded


def _patch_cohort_dataframe_persistence(monkeypatch, tmp_path: Path) -> None:
    def _persist_dataframe_as_csv(db, version, df, time_column) -> None:
        storage_path = tmp_path / "cohort-derived" / f"{version.dataset_version_id}.csv"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(storage_path, index=False)
        version.storage_ref = str(storage_path)
        version.row_count = int(len(df))
        db.flush()

    monkeypatch.setattr(dataframe_io, "persist_dataframe_as_version_rows", _persist_dataframe_as_csv)


def _gate_b_decision(candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate["source_class"] in {"dataset_version", "aps_content_document"}:
        return _approved_decision(candidate)
    return {
        "candidate_id": candidate["candidate_id"],
        "decision": "flagged",
        "operator_reason": "APS qualitative companion remains deferred for the current quantitative cohort path.",
        "decision_basis": _decision_basis(candidate),
    }


def _approved_decision(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "decision": "approved",
        "decision_basis": _decision_basis(candidate),
    }


def _decision_basis(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": candidate["source_identity"],
        "source_provenance": candidate["source_provenance"],
        "payload": candidate["payload"],
        "load_summary": candidate["load_summary"],
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


def _assert_aps_doc_source_preview(source: dict[str, Any]) -> None:
    assert source["unsupported_sources"] == []
    assert [candidate["source_class"] for candidate in source["source_candidates"]] == ["aps_content_document"]
    candidate = source["source_candidates"][0]
    assert candidate["source_candidate_id"]
    assert candidate["source_class"] == "aps_content_document"


def _assert_aps_doc_material_preview(material: dict[str, Any], *, seeded: SeededApsDocument) -> None:
    candidates = material["material_candidates"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["source_class"] == "aps_content_document"
    assert candidate["source_identity"]["content_id"] == seeded.aps_content_id
    assert candidate["source_provenance"]["aps_derived"] is True
    assert candidate["source_trace"]["trace_readiness"] == "traceable_aps_content_document"
    assert candidate["source_trace"]["aps_trace_refs"]["run_id"] == seeded.aps_run_id
    assert candidate["source_trace"]["aps_trace_refs"]["target_id"] == seeded.aps_target_id
    assert candidate["load_summary"]["loaded_records"] == 2
    assert candidate["load_summary"]["failed_records"] == 0


def _assert_descriptive_cohort_plan_preview(plan_preview: dict[str, Any], *, seeded: SeededSources) -> None:
    payload = plan_preview["plan_preview"]
    assert payload["approval_ready"] is True
    assert len(payload["admitted_sets"]) == 1
    assert len(payload["excluded_sets"]) == 1
    assert payload["excluded_sets"][0]["reason_code"] == "qualitative_aps_companion_provenance_not_pass_candidate"
    assert payload["excluded_sets"][0]["analysis_modality"] == "qualitative"
    assert len(payload["planned_passes"]) == 1
    planned_pass = payload["planned_passes"][0]
    assert planned_pass["pass_type"] == "associated_cohort"
    assert planned_pass["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert planned_pass["selected_method_name"] == "descriptive_summary"
    assert sorted(planned_pass["source_dataset_version_ids"]) == sorted(seeded.dataset_version_ids)


def _assert_single_aps_doc_qualitative_plan_preview(
    plan_preview: dict[str, Any],
) -> None:
    payload = plan_preview["plan_preview"]
    assert payload["approval_ready"] is True
    assert len(payload["admitted_sets"]) == 1
    assert payload["excluded_sets"] == []
    assert len(payload["planned_passes"]) == 1
    planned_pass = payload["planned_passes"][0]
    assert planned_pass["pass_type"] == "single_item"
    assert planned_pass["pass_scope"] == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
    assert planned_pass["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert planned_pass["selected_method_name"] == QUAL_APS_METHOD_NAME


def _assert_single_aps_doc_qualitative_output(
    start: dict[str, Any],
    *,
    seeded: SeededApsDocument,
) -> dict[str, Any]:
    output = json.loads(Path(start["output_payload_ref"]).read_text(encoding="utf-8"))
    assert output["schema_id"] == QUAL_APS_OUTPUT_SCHEMA_ID
    assert output["analysis_run_id"] is None
    assert output["document_identity"]["content_id"] == seeded.aps_content_id
    assert output["chunk_summary"]["ordering"] == "chunk_ordinal_then_chunk_id"
    assert output["chunk_summary"]["chunk_ids"] == [
        f"{seeded.aps_content_id}-chunk-1",
        f"{seeded.aps_content_id}-chunk-2",
    ]
    assert len(output["output_items_json"]) == 2
    assert output["output_items_json"][0]["trace"]["chunk_id"] == f"{seeded.aps_content_id}-chunk-1"
    return output


def _assert_single_aps_doc_qualitative_package_preview(
    package_preview: dict[str, Any],
    *,
    output: dict[str, Any],
    seeded: SeededApsDocument,
    start: dict[str, Any],
) -> None:
    assert package_preview["schema_id"] == "layer3.qual_aps_package_review_preview.v1"
    assert package_preview["status"] == "available"
    assert package_preview["analysis_run_id"] is None
    assert package_preview["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert package_preview["pass_type"] == "single_item"
    assert package_preview["pass_scope"] == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
    assert package_preview["method"] == QUAL_APS_METHOD_NAME
    assert package_preview["selected_method_name"] == QUAL_APS_METHOD_NAME
    assert package_preview["source_gate"] == QUAL_APS_SOURCE_GATE
    assert package_preview["source_shape"] == "aps_content_document"
    assert package_preview["source_dataset_version_ids"] == []
    assert package_preview["content_id"] == seeded.aps_content_id
    assert package_preview["content_contract_id"] == output["document_identity"]["content_contract_id"]
    assert package_preview["chunking_contract_id"] == output["document_identity"]["chunking_contract_id"]
    assert package_preview["material_snapshot_id"] == output["material_snapshot_id"]
    assert package_preview["analysis_unit_id"] == output["analysis_unit_id"]
    assert package_preview["analysis_set_id"] == output["analysis_set_id"]
    assert package_preview["output_payload_ref"] == start["output_payload_ref"]
    assert package_preview["output_payload_hash"] == output["output_hash"]
    assert package_preview["chunk_count"] == output["chunk_summary"]["chunk_count"]
    assert package_preview["package_review_preview_enabled"] is True
    assert package_preview["package_commit_enabled"] is True
    assert package_preview["package_review_enabled"] is False
    assert package_preview["package_review_submit_enabled"] is False
    assert package_preview["handoff_enabled"] is False
    assert package_preview["aps_handoff_enabled"] is False
    assert package_preview["external_export_download_enabled"] is False
    assert package_preview["connector_dispatch_enabled"] is False
    assert package_preview["provider_public_url_enabled"] is False
    assert package_preview["blocked_reasons"] == []
    assert "package_construction" not in package_preview["downstream_unavailable"]
    assert "package_review_submit" in package_preview["downstream_unavailable"]
    assert "external_export_download" in package_preview["downstream_unavailable"]
    assert package_preview["package_owner_compatibility"]["workbench_package_commit_callable"] is True
    assert package_preview["package_owner_compatibility"]["missing_owner_service_inputs"] == []
    assert [candidate["package_kind"] for candidate in package_preview["candidate_package_kinds"]] == [
        "canonical_internal",
        "user_facing",
        "review_facing",
    ]
    assert all(candidate["preview_only"] is True for candidate in package_preview["candidate_package_kinds"])
    assert all(candidate["package_commit_enabled"] is True for candidate in package_preview["candidate_package_kinds"])
    assert package_preview["output_metadata_summary"]["content_id"] == seeded.aps_content_id
    assert package_preview["output_metadata_summary"]["chunk_ids"] == output["chunk_summary"]["chunk_ids"]
    _assert_response_refs_exist(package_preview)
    _assert_forbidden_response_surface_absent(package_preview)


def _assert_single_aps_doc_qualitative_package_commit(
    package_commit: dict[str, Any],
    *,
    package_preview: dict[str, Any],
    output: dict[str, Any],
    seeded: SeededApsDocument,
) -> None:
    assert package_commit["schema_id"] == "layer3.qual_aps_package_construction_commit.v1"
    assert package_commit["status"] == "committed"
    assert package_commit["analysis_run_id"] is None
    assert package_commit["package_review_preview_hash"] == package_preview["package_review_preview_hash"]
    assert package_commit["construction_basis_hash"]
    assert package_commit["package_construction_source_gate"] == "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE"
    assert package_commit["package_review_submit_enabled"] is True
    assert package_commit["handoff_enabled"] is False
    assert package_commit["aps_handoff_enabled"] is False
    assert package_commit["external_export_download_enabled"] is False
    assert package_commit["connector_dispatch_enabled"] is False
    assert package_commit["provider_public_url_enabled"] is False
    assert "package_review_submit" not in package_commit["downstream_unavailable"]
    assert "handoff" in package_commit["downstream_unavailable"]
    assert "external_export_download" in package_commit["downstream_unavailable"]
    assert package_commit["content_id"] == seeded.aps_content_id
    assert package_commit["content_contract_id"] == output["document_identity"]["content_contract_id"]
    assert package_commit["chunking_contract_id"] == output["document_identity"]["chunking_contract_id"]
    assert package_commit["material_snapshot_id"] == output["material_snapshot_id"]
    assert package_commit["analysis_unit_id"] == output["analysis_unit_id"]
    assert package_commit["analysis_set_id"] == output["analysis_set_id"]
    assert package_commit["output_payload_hash"] == output["output_hash"]
    assert package_commit["source_shape"] == "aps_content_document"
    assert package_commit["source_dataset_version_ids"] == []
    assert package_commit["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert len(package_commit["output_packages"]) == 3
    assert package_commit["output_package_ids"] == [
        package["output_package_id"] for package in package_commit["output_packages"]
    ]
    _assert_response_refs_exist(package_commit)
    for package in package_commit["output_packages"]:
        payload = json.loads(Path(package["payload_ref"]).read_text(encoding="utf-8"))
        assert payload["package_header"]["source_gate"] == "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE"
        assert payload["negative_capability_flags"]["package_review_submit_enabled"] is False
        assert payload["negative_capability_flags"]["provider_public_url_enabled"] is False
        if package["package_kind"] == "canonical_internal":
            assert payload["qualitative_output_payload"]["output_hash"] == output["output_hash"]
            assert payload["qualitative_source_authority"]["content_id"] == seeded.aps_content_id
        if package["package_kind"] == "review_facing":
            assert payload["chunk_trace"]["chunk_ids"] == output["chunk_summary"]["chunk_ids"]
    _assert_forbidden_response_surface_absent(package_commit)


def _assert_forbidden_response_surface_absent(payload: Any) -> None:
    forbidden_keys = {
        "artifact_manifest",
        "browser_state",
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


def _assert_response_refs_exist(payload: dict[str, Any]) -> None:
    for key in ("input_payload_ref", "output_payload_ref", "source_artifact_ref", "aps_bundle_ref"):
        ref = payload.get(key)
        if ref:
            assert Path(ref).exists()
    for ref in payload.get("payload_refs") or []:
        assert Path(ref).exists()
    for package in payload.get("output_packages") or []:
        _assert_file_sha256(package["payload_ref"], package["payload_hash"])
