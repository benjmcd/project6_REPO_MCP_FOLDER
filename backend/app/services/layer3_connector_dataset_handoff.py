"""Review-only package handoff for connector-only Gate-B material."""

from __future__ import annotations

from typing import Any, NoReturn

from sqlalchemy.orm import Session

from app.models.models import (
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
    uuid_str,
)
from app.services.layer3_connector_promotion_identity import (
    ConnectorPromotionIdentityError,
    derive_candidate_identity,
)
from app.services.layer3_connector_source_intake import (
    CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX,
    CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_STATUS_REVIEW_ONLY,
    RECONCILIATION_STATUS_REVIEW_ONLY,
    Layer3PackageEntryResult,
    _existing_workbench_package_result,
    _json_clone,
    _output_package_summary,
    _package_header,
    _persist_package_payload,
    _stable_hash,
)


CONNECTOR_DATASET_HANDOFF_AUTHORITY_SCHEMA_ID = (
    "layer3.connector_dataset_handoff_authority.v1"
)
CONNECTOR_DATASET_HANDOFF_PAYLOAD_SCHEMA_ID = (
    "layer3.connector_dataset_handoff_package_payload.v1"
)
CONNECTOR_DATASET_HANDOFF_COMMIT_SCHEMA_ID = (
    "layer3.connector_dataset_handoff_package_commit_summary.v1"
)
SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE = (
    "CONNECTOR_DATASET_HANDOFF_PACKAGE_CONSTRUCTION_FREEZE"
)

PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

DOWNSTREAM_UNAVAILABLE = {
    "package_review_submit_enabled": False,
    "handoff_enabled": False,
    "external_export_download_enabled": False,
    "connector_dispatch_enabled": False,
    "provider_public_delivery_enabled": False,
    "frontend_durable_authority_enabled": False,
}

DOWNSTREAM_UNAVAILABLE_ACTIONS = (
    "package_review_submit",
    "handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_delivery",
    "frontend_durable_authority",
)

NEGATIVE_INVARIANTS = {
    "source_package_row_mutation_enabled": False,
    "package_payload_rewrite_enabled": False,
    "package_review_submit_enabled": False,
    "handoff_export_enabled": False,
    "connector_dispatch_enabled": False,
    "provider_public_delivery_enabled": False,
    "network_egress_enabled": False,
    "frontend_durable_authority_enabled": False,
    "prompt_model_provider_runtime_enabled": False,
}


def _not_eligible() -> NoReturn:
    raise ConnectorPromotionIdentityError(
        "connector_promotion_not_eligible",
        "Connector promotion candidate is not eligible.",
    )


def _validate_durable_lineage(
    db: Session,
    *,
    session: L3Session,
    promotion_receipt: L3ConnectorPromotionReceipt,
    intake_record: L3ConnectorSourceIntakeRecord,
    material_snapshot: L3MaterialSnapshot,
    manifest: L3SelectionManifest,
) -> None:
    if (
        promotion_receipt.gate_b_session_id != session.session_id
        or promotion_receipt.gate_b_selection_manifest_id
        != manifest.selection_manifest_id
        or promotion_receipt.gate_b_material_snapshot_id
        != material_snapshot.material_snapshot_id
        or promotion_receipt.connector_source_intake_record_id
        != intake_record.connector_source_intake_record_id
        or manifest.session_id != session.session_id
        or session.selection_manifest_id != manifest.selection_manifest_id
        or material_snapshot.session_id != session.session_id
        or material_snapshot.source_shape != CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
    ):
        _not_eligible()

    identity = derive_candidate_identity(
        db,
        {
            "candidate_id": (
                f"{CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX}"
                f"{intake_record.connector_source_intake_record_id}"
            )
        },
    )
    if (
        identity.connector_source_intake_record_id
        != intake_record.connector_source_intake_record_id
        or identity.identity_metadata_hash_version
        != promotion_receipt.identity_metadata_hash_version
        or identity.source_family != promotion_receipt.source_family
        or identity.content_sha256 != intake_record.content_sha256
        or identity.content_sha256 != promotion_receipt.content_sha256
        or identity.identity_metadata_hash != intake_record.identity_metadata_hash
        or identity.identity_metadata_hash != promotion_receipt.identity_metadata_hash
        or identity.canonical_identity_key_hash
        != promotion_receipt.canonical_identity_key_hash
    ):
        _not_eligible()

    snapshot_identity = material_snapshot.source_identity_json or {}
    expected_snapshot_identity = {
        "connector_source_intake_record_id": intake_record.connector_source_intake_record_id,
        "connector_run_id": intake_record.connector_run_id,
        "connector_run_target_id": intake_record.connector_run_target_id,
        "content_sha256": intake_record.content_sha256,
        "source_family": intake_record.source_family,
    }
    if any(
        snapshot_identity.get(field) != value
        for field, value in expected_snapshot_identity.items()
    ):
        _not_eligible()

    snapshot_provenance = material_snapshot.source_provenance_json or {}
    expected_snapshot_provenance = {
        "connector_key": intake_record.connector_key,
        "connector_run_id": intake_record.connector_run_id,
        "connector_run_target_id": intake_record.connector_run_target_id,
        "content_sha256": intake_record.content_sha256,
        "metadata_hash": intake_record.metadata_hash,
    }
    if any(
        snapshot_provenance.get(field) != value
        for field, value in expected_snapshot_provenance.items()
    ):
        _not_eligible()

    _validated_load_summary(material_snapshot)


def _nonnegative_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _not_eligible()
    return value


def _validated_load_summary(
    material_snapshot: L3MaterialSnapshot,
) -> dict[str, int]:
    load_summary = material_snapshot.load_summary_json or {}
    return {
        "loaded_records": _nonnegative_count(load_summary.get("loaded_records")),
        "failed_records": _nonnegative_count(load_summary.get("failed_records")),
    }


def _connector_source_summary(
    *,
    session: L3Session,
    intake_record: L3ConnectorSourceIntakeRecord,
    material_snapshot: L3MaterialSnapshot,
    manifest: L3SelectionManifest,
) -> dict[str, Any]:
    intake_record_id = intake_record.connector_source_intake_record_id
    return {
        "session_id": session.session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_plane": material_snapshot.source_plane,
        "source_shape": material_snapshot.source_shape,
        "source_identity": {
            "candidate_id": (
                f"{CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX}"
                f"{intake_record_id}"
            ),
            "source_class": CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
            "connector_source_intake_record_id": intake_record_id,
            "connector_run_id": intake_record.connector_run_id,
            "connector_run_target_id": intake_record.connector_run_target_id,
            "content_sha256": intake_record.content_sha256,
            "source_family": intake_record.source_family,
            "metadata_hash": intake_record.metadata_hash,
        },
        "source_provenance": {
            "source_ref": f"connector_source_intake_record:{intake_record_id}",
            "provenance_ref": (
                f"connector_source_intake_record:{intake_record_id}:"
                f"metadata:{intake_record.metadata_hash}"
            ),
            "connector_source_intake_record_id": intake_record_id,
            "connector_key": intake_record.connector_key,
            "connector_run_id": intake_record.connector_run_id,
            "connector_run_target_id": intake_record.connector_run_target_id,
            "content_sha256": intake_record.content_sha256,
            "metadata_hash": intake_record.metadata_hash,
            "authority_basis_hash": intake_record.authority_basis_hash,
        },
        "load_summary": _validated_load_summary(material_snapshot),
        "material_payload_hash": material_snapshot.payload_hash,
        "connector_source_intake_record_id": intake_record_id,
        "connector_run_id": intake_record.connector_run_id,
        "connector_run_target_id": intake_record.connector_run_target_id,
        "content_sha256": intake_record.content_sha256,
        "content_size_bytes": intake_record.content_size_bytes,
        "media_type": intake_record.media_type,
    }


def _promotion_receipt_binding(
    promotion_receipt: L3ConnectorPromotionReceipt,
) -> dict[str, str]:
    return {
        "connector_promotion_receipt_id": (
            promotion_receipt.connector_promotion_receipt_id
        ),
        "canonical_identity_key_hash": (
            promotion_receipt.canonical_identity_key_hash
        ),
        "approval_hash": promotion_receipt.approval_hash,
        "promotion_basis_hash": promotion_receipt.promotion_basis_hash,
    }


def _package_payload(
    *,
    session_id: str,
    package_kind: str,
    canonical_package_key: str | None,
    authority_basis: dict[str, Any],
    authority_basis_hash: str,
    connector_source_summary: dict[str, Any],
    promotion_receipt_binding: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_id": CONNECTOR_DATASET_HANDOFF_PAYLOAD_SCHEMA_ID,
        "package_header": _package_header(
            session_id=session_id,
            package_kind=package_kind,
            package_status=PACKAGE_STATUS_REVIEW_ONLY,
            canonical_package_key=canonical_package_key,
            source_gate=SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE,
        ),
        "package_family": "connector_dataset_handoff",
        "authority_basis": _json_clone(authority_basis),
        "authority_basis_hash": authority_basis_hash,
        "connector_source_summary": _json_clone(connector_source_summary),
        "promotion_receipt_binding": _json_clone(promotion_receipt_binding),
        "analysis_plan_id": None,
        "pass_run_ids": [],
        "handoff_enabled": False,
        "package_lifecycle": {
            "package_construction_enabled": True,
            "package_mutation_enabled": False,
            "source_package_row_mutation_enabled": False,
            "package_payload_rewrite_enabled": False,
        },
        "downstream_unavailable": _json_clone(DOWNSTREAM_UNAVAILABLE),
        "negative_invariants": _json_clone(NEGATIVE_INVARIANTS),
    }


def build_connector_dataset_handoff(
    db: Session,
    *,
    session: L3Session,
    promotion_receipt: L3ConnectorPromotionReceipt,
    intake_record: L3ConnectorSourceIntakeRecord,
    material_snapshot: L3MaterialSnapshot,
    manifest: L3SelectionManifest,
    client_request_id: str,
) -> Layer3PackageEntryResult:
    authority_basis = {
        "schema_id": CONNECTOR_DATASET_HANDOFF_AUTHORITY_SCHEMA_ID,
        "session_id": session.session_id,
        "connector_promotion_receipt_id": (
            promotion_receipt.connector_promotion_receipt_id
        ),
        "canonical_identity_key_hash": (
            promotion_receipt.canonical_identity_key_hash
        ),
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "client_request_id": client_request_id,
        "source_gate": SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE,
    }
    authority_basis_hash = _stable_hash(authority_basis)
    existing = _existing_workbench_package_result(
        db,
        session_id=session.session_id,
        authority_basis_hash=authority_basis_hash,
        client_request_id=client_request_id,
    )
    if existing is not None:
        return existing

    _validate_durable_lineage(
        db,
        session=session,
        promotion_receipt=promotion_receipt,
        intake_record=intake_record,
        material_snapshot=material_snapshot,
        manifest=manifest,
    )

    source_summary = _connector_source_summary(
        session=session,
        intake_record=intake_record,
        material_snapshot=material_snapshot,
        manifest=manifest,
    )
    receipt_binding = _promotion_receipt_binding(promotion_receipt)
    canonical_payload = _package_payload(
        session_id=session.session_id,
        package_kind=PACKAGE_KIND_CANONICAL_INTERNAL,
        canonical_package_key=None,
        authority_basis=authority_basis,
        authority_basis_hash=authority_basis_hash,
        connector_source_summary=source_summary,
        promotion_receipt_binding=receipt_binding,
    )
    canonical_key = canonical_payload["package_header"]["package_key"]
    package_payloads = {
        PACKAGE_KIND_CANONICAL_INTERNAL: canonical_payload,
        PACKAGE_KIND_USER_FACING: _package_payload(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_USER_FACING,
            canonical_package_key=canonical_key,
            authority_basis=authority_basis,
            authority_basis_hash=authority_basis_hash,
            connector_source_summary=source_summary,
            promotion_receipt_binding=receipt_binding,
        ),
        PACKAGE_KIND_REVIEW_FACING: _package_payload(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_REVIEW_FACING,
            canonical_package_key=canonical_key,
            authority_basis=authority_basis,
            authority_basis_hash=authority_basis_hash,
            connector_source_summary=source_summary,
            promotion_receipt_binding=receipt_binding,
        ),
    }

    reconciliation_summary: dict[str, Any] = {
        "analysis_plan_id": None,
        "pass_run_ids_json": [],
        "accepted_pass_run_ids_json": [],
        "warning_pass_run_ids_json": [],
        "failed_pass_run_ids_json": [],
        "package_status": PACKAGE_STATUS_REVIEW_ONLY,
        "source_gate": SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE,
        "workbench_package_commit": {
            "schema_id": CONNECTOR_DATASET_HANDOFF_COMMIT_SCHEMA_ID,
            "client_request_id": client_request_id,
            "authority_basis": _json_clone(authority_basis),
            "authority_basis_hash": authority_basis_hash,
            "analysis_plan_id": None,
            "pass_run_ids": [],
            "source_gate": SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE,
            "package_construction_source_gate": (
                SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE
            ),
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "downstream_unavailable": list(DOWNSTREAM_UNAVAILABLE_ACTIONS),
        },
    }
    reconciliation_record = L3ReconciliationRecord(
        reconciliation_record_id=uuid_str(),
        session_id=session.session_id,
        status=RECONCILIATION_STATUS_REVIEW_ONLY,
        summary_json=reconciliation_summary,
    )
    db.add(reconciliation_record)
    db.flush()

    package_rows: list[L3OutputPackage] = []
    for package_kind in PACKAGE_KINDS:
        payload = package_payloads[package_kind]
        payload_ref, payload_hash = _persist_package_payload(
            session_id=session.session_id,
            package_kind=package_kind,
            payload=payload,
        )
        package_rows.append(
            L3OutputPackage(
                output_package_id=uuid_str(),
                session_id=session.session_id,
                reconciliation_record_id=(
                    reconciliation_record.reconciliation_record_id
                ),
                package_kind=package_kind,
                status=PACKAGE_STATUS_REVIEW_ONLY,
                payload_ref=payload_ref,
                payload_hash=payload_hash,
                summary_json=_output_package_summary(
                    package_kind=package_kind,
                    payload=payload,
                    package_status=PACKAGE_STATUS_REVIEW_ONLY,
                    findings=[],
                    contradictions=[],
                    caveats=[],
                    source_gate=SOURCE_CONNECTOR_DATASET_HANDOFF_FREEZE,
                ),
            )
        )
    db.add_all(package_rows)
    db.flush()

    construction_basis_hash = _stable_hash(
        {
            **authority_basis,
            "package_kinds": [package.package_kind for package in package_rows],
            "payload_hashes": [package.payload_hash for package in package_rows],
        }
    )
    reconciliation_record.summary_json = {
        **reconciliation_summary,
        "workbench_package_commit": {
            **reconciliation_summary["workbench_package_commit"],
            "construction_basis_hash": construction_basis_hash,
        },
    }
    for package in package_rows:
        package.summary_json = {
            **_json_clone(package.summary_json or {}),
            "construction_basis_hash": construction_basis_hash,
        }
    db.flush()
    return Layer3PackageEntryResult(
        reconciliation_record=reconciliation_record,
        output_packages=tuple(package_rows),
        replayed=False,
    )
