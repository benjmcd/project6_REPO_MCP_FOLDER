from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    CaveatNote,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3Descriptor,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    uuid_str,
)
from app.services.layer3_pass_entry import (
    PASS_STATUS_COMPLETED,
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
)
from app.services.layer3_session_entry import (
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_COMPLETED_WITH_WARNINGS,
    SESSION_STATUS_FAILED,
)
from app.services.layer3_utils import (
    json_text_clone as _json_clone,
    stable_json_text as _stable_json_text,
    stable_json_text_bytes as _stable_json_bytes,
    stable_json_text_hash as _stable_hash,
)


PACKAGE_KIND_CANONICAL_INTERNAL = "canonical_internal"
PACKAGE_KIND_USER_FACING = "user_facing"
PACKAGE_KIND_REVIEW_FACING = "review_facing"

PACKAGE_STATUS_COMPLETE = "package_complete"
PACKAGE_STATUS_COMPLETE_WITH_WARNINGS = "package_complete_with_warnings"
PACKAGE_STATUS_REVIEW_ONLY = "package_review_only"
PACKAGE_STATUS_HANDOFF_BLOCKED = "package_handoff_blocked"
PACKAGE_STATUS_FAILED = "package_failed"

RECONCILIATION_STATUS_RECONCILED = "reconciled"
RECONCILIATION_STATUS_RECONCILED_WITH_WARNINGS = "reconciled_with_warnings"
RECONCILIATION_STATUS_REVIEW_ONLY = "review_only"

SOURCE_GATE_D_PACKAGE_FREEZE = "08_GATED_PACKAGE_FREEZE"
SOURCE_WORKBENCH_PACKAGE_CONSTRUCTION_FREEZE = "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE"
SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE = "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE = "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE"
PACKAGE_SCHEMA_VERSION = 1

FINALIZED_PACKAGE_SESSION_STATUSES = frozenset(
    {
        SESSION_STATUS_COMPLETED,
        SESSION_STATUS_COMPLETED_WITH_WARNINGS,
        SESSION_STATUS_FAILED,
    }
)
TERMINAL_PASS_STATUSES = frozenset(
    {
        PASS_STATUS_COMPLETED,
        PASS_STATUS_COMPLETED_WITH_WARNINGS,
        PASS_STATUS_FAILED,
    }
)
ACCEPTED_PASS_STATUSES = frozenset(
    {
        PASS_STATUS_COMPLETED,
        PASS_STATUS_COMPLETED_WITH_WARNINGS,
    }
)

PACKAGE_SCHEMA_IDS = {
    PACKAGE_KIND_CANONICAL_INTERNAL: "layer3.canonical_internal_package.v1",
    PACKAGE_KIND_USER_FACING: "layer3.user_facing_package.v1",
    PACKAGE_KIND_REVIEW_FACING: "layer3.review_facing_package.v1",
}


class Layer3PackageEntryError(ValueError):
    pass


@dataclass(frozen=True)
class Layer3PackageEntryResult:
    reconciliation_record: L3ReconciliationRecord
    output_packages: tuple[L3OutputPackage, ...]
    replayed: bool = False


def _safe_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return "".join(char for char in raw if char.isalnum() or char in {"_", "-", "."}) or "unknown"


def _package_key(*, session_id: str, package_kind: str) -> str:
    return f"l3:{session_id}:{package_kind}"


def _package_artifact_dir() -> Path:
    path = Path(settings.artifact_storage_dir) / "layer3"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _package_artifact_path(*, session_id: str, package_kind: str, payload_hash: str) -> Path:
    return _package_artifact_dir() / (
        f"l3_package_{_safe_token(session_id)}_{_safe_token(package_kind)}_{payload_hash[:12]}.json"
    )


def _persist_package_payload(*, session_id: str, package_kind: str, payload: dict[str, Any]) -> tuple[str, str]:
    payload_bytes = _stable_json_bytes(payload)
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    payload_path = _package_artifact_path(
        session_id=session_id,
        package_kind=package_kind,
        payload_hash=payload_hash,
    )
    if not payload_path.exists():
        payload_path.write_bytes(payload_bytes)
    return str(payload_path), payload_hash


def _require_existing_ref(ref: str | None, *, label: str) -> str:
    normalized = str(ref or "").strip()
    if not normalized:
        raise Layer3PackageEntryError(f"{label} is missing")
    if not Path(normalized).exists():
        raise Layer3PackageEntryError(f"{label} does not exist: {normalized}")
    return normalized


def _load_session_or_raise(db: Session, *, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' was not found")
    if session.status not in FINALIZED_PACKAGE_SESSION_STATUSES or session.completed_at is None:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' must be terminal before Gate D package entry"
        )
    summary = dict(session.summary_json or {})
    if not isinstance(summary.get("phase1a_loading_closure"), dict):
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' is missing phase1a_loading_closure required for Gate D package entry"
        )
    if not isinstance(summary.get("pass_entry"), dict):
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' is missing pass_entry required for Gate D package entry"
        )
    return session


def _ensure_session_not_yet_packaged(db: Session, *, session_id: str) -> None:
    if (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .first()
        is not None
    ):
        raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' already has a reconciliation record")
    if db.query(L3OutputPackage).filter(L3OutputPackage.session_id == session_id).first() is not None:
        raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' already has output packages")


def _load_selection_context(
    db: Session,
    *,
    session_id: str,
) -> tuple[L3SelectionManifest, list[L3Descriptor], list[L3MaterialSnapshot]]:
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session_id)
        .one_or_none()
    )
    if manifest is None:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' is missing a selection manifest required for Gate D package entry"
        )
    descriptors = (
        db.query(L3Descriptor)
        .filter(L3Descriptor.session_id == session_id)
        .order_by(L3Descriptor.descriptor_id.asc())
        .all()
    )
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
        .all()
    )
    if not descriptors:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' has no descriptors required for Gate D package entry"
        )
    if not snapshots:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' has no material snapshots required for Gate D package entry"
        )
    for snapshot in snapshots:
        _require_existing_ref(
            snapshot.payload_ref,
            label=f"Layer 3 material snapshot '{snapshot.material_snapshot_id}' payload ref",
        )
    return manifest, descriptors, snapshots


def _load_typing_context(
    db: Session,
    *,
    session_id: str,
) -> tuple[list[L3TypingRecord], list[L3AnalysisUnit], list[L3AnalysisGroup], list[L3AnalysisSet]]:
    typings = (
        db.query(L3TypingRecord)
        .filter(L3TypingRecord.session_id == session_id)
        .order_by(L3TypingRecord.typing_record_id.asc())
        .all()
    )
    analysis_units = (
        db.query(L3AnalysisUnit)
        .filter(L3AnalysisUnit.session_id == session_id)
        .order_by(L3AnalysisUnit.analysis_unit_id.asc())
        .all()
    )
    analysis_groups = (
        db.query(L3AnalysisGroup)
        .filter(L3AnalysisGroup.session_id == session_id)
        .order_by(L3AnalysisGroup.analysis_group_id.asc())
        .all()
    )
    analysis_sets = (
        db.query(L3AnalysisSet)
        .filter(L3AnalysisSet.session_id == session_id)
        .order_by(L3AnalysisSet.analysis_set_id.asc())
        .all()
    )
    if not analysis_sets:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session_id}' has no analysis sets required for Gate D package entry"
        )
    return typings, analysis_units, analysis_groups, analysis_sets


def _pass_entry_summary(session: L3Session) -> dict[str, Any]:
    summary = dict(session.summary_json or {})
    pass_entry = dict(summary.get("pass_entry") or {})
    if not pass_entry:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session.session_id}' is missing pass_entry required for Gate D package entry"
        )
    return pass_entry


def _load_plan_and_pass_runs(
    db: Session,
    *,
    session: L3Session,
) -> tuple[L3AnalysisPlan, list[L3PassRun], list[dict[str, Any]]]:
    pass_entry = _pass_entry_summary(session)
    analysis_plan_id = str(pass_entry.get("analysis_plan_id") or "").strip()
    if not analysis_plan_id:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session.session_id}' has no analysis_plan_id in pass_entry"
        )
    analysis_plan = db.get(L3AnalysisPlan, analysis_plan_id)
    if analysis_plan is None or analysis_plan.session_id != session.session_id:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session.session_id}' has broken analysis plan provenance for Gate D package entry"
        )

    pass_run_ids = [
        str(item).strip()
        for item in list(pass_entry.get("pass_run_ids_json") or [])
        if str(item).strip()
    ]
    if not pass_run_ids:
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session.session_id}' has no pass runs required for Gate D package entry"
        )
    all_session_pass_runs = (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == session.session_id)
        .order_by(L3PassRun.created_at.asc(), L3PassRun.pass_run_id.asc())
        .all()
    )
    pass_run_by_id = {pass_run.pass_run_id: pass_run for pass_run in all_session_pass_runs}
    if set(pass_run_by_id) != set(pass_run_ids):
        raise Layer3PackageEntryError(
            f"Layer 3 session '{session.session_id}' has pass-entry rows that do not match session pass provenance"
        )
    ordered_pass_runs = [pass_run_by_id[pass_run_id] for pass_run_id in pass_run_ids]
    for pass_run in ordered_pass_runs:
        if pass_run.analysis_plan_id != analysis_plan.analysis_plan_id:
            raise Layer3PackageEntryError(
                f"Layer 3 pass run '{pass_run.pass_run_id}' does not point back to the session analysis plan"
            )
        if pass_run.status not in TERMINAL_PASS_STATUSES:
            raise Layer3PackageEntryError(
                f"Layer 3 pass run '{pass_run.pass_run_id}' must be terminal before Gate D package entry"
            )
    excluded_sets = [dict(item or {}) for item in list(pass_entry.get("excluded_sets_json") or []) if isinstance(item, dict)]
    return analysis_plan, ordered_pass_runs, excluded_sets


def _analysis_run_id(pass_run: L3PassRun) -> str | None:
    value = str((pass_run.summary_json or {}).get("analysis_run_id") or "").strip()
    return value or None


def _validate_pass_provenance(
    db: Session,
    *,
    pass_runs: list[L3PassRun],
) -> dict[str, AnalysisRun]:
    analysis_runs_by_id: dict[str, AnalysisRun] = {}
    for pass_run in pass_runs:
        _require_existing_ref(
            pass_run.input_payload_ref,
            label=f"Layer 3 pass run '{pass_run.pass_run_id}' input payload ref",
        )
        analysis_run_id = _analysis_run_id(pass_run)
        if pass_run.status in ACCEPTED_PASS_STATUSES:
            _require_existing_ref(
                pass_run.output_payload_ref,
                label=f"Layer 3 pass run '{pass_run.pass_run_id}' output payload ref",
            )
            if not analysis_run_id:
                raise Layer3PackageEntryError(
                    f"Layer 3 pass run '{pass_run.pass_run_id}' is missing analysis_run_id required for package entry"
                )
            analysis_run = db.get(AnalysisRun, analysis_run_id)
            if analysis_run is None:
                raise Layer3PackageEntryError(
                    f"Layer 3 pass run '{pass_run.pass_run_id}' points at a missing analysis run"
                )
            analysis_runs_by_id[analysis_run_id] = analysis_run
            continue

        if pass_run.status == PASS_STATUS_FAILED:
            error_message = str((pass_run.summary_json or {}).get("error") or "").strip()
            if not error_message:
                raise Layer3PackageEntryError(
                    f"Layer 3 failed pass run '{pass_run.pass_run_id}' is missing failure provenance"
                )
            if analysis_run_id:
                analysis_run = db.get(AnalysisRun, analysis_run_id)
                if analysis_run is None:
                    raise Layer3PackageEntryError(
                        f"Layer 3 failed pass run '{pass_run.pass_run_id}' points at a missing analysis run"
                    )
                analysis_runs_by_id[analysis_run_id] = analysis_run
    return analysis_runs_by_id


def _load_artifacts_by_run(
    db: Session,
    *,
    analysis_run_ids: list[str],
) -> dict[str, list[AnalysisArtifact]]:
    if not analysis_run_ids:
        return {}
    artifacts = (
        db.query(AnalysisArtifact)
        .filter(AnalysisArtifact.analysis_run_id.in_(analysis_run_ids))
        .order_by(AnalysisArtifact.created_at.asc(), AnalysisArtifact.artifact_id.asc())
        .all()
    )
    grouped: dict[str, list[AnalysisArtifact]] = {analysis_run_id: [] for analysis_run_id in analysis_run_ids}
    for artifact in artifacts:
        grouped.setdefault(artifact.analysis_run_id, []).append(artifact)
    return grouped


def _load_caveats_by_run(
    db: Session,
    *,
    analysis_run_ids: list[str],
) -> dict[str, list[CaveatNote]]:
    if not analysis_run_ids:
        return {}
    caveats = (
        db.query(CaveatNote)
        .filter(CaveatNote.analysis_run_id.in_(analysis_run_ids))
        .order_by(CaveatNote.created_at.asc(), CaveatNote.caveat_note_id.asc())
        .all()
    )
    grouped: dict[str, list[CaveatNote]] = {analysis_run_id: [] for analysis_run_id in analysis_run_ids}
    for caveat in caveats:
        grouped.setdefault(caveat.analysis_run_id, []).append(caveat)
    return grouped


def _accepted_pass_run_ids(pass_runs: list[L3PassRun]) -> list[str]:
    return [pass_run.pass_run_id for pass_run in pass_runs if pass_run.status in ACCEPTED_PASS_STATUSES]


def _warning_pass_run_ids(pass_runs: list[L3PassRun]) -> list[str]:
    return [pass_run.pass_run_id for pass_run in pass_runs if pass_run.status == PASS_STATUS_COMPLETED_WITH_WARNINGS]


def _failed_pass_run_ids(pass_runs: list[L3PassRun]) -> list[str]:
    return [pass_run.pass_run_id for pass_run in pass_runs if pass_run.status == PASS_STATUS_FAILED]


def _package_status(
    *,
    session: L3Session,
    pass_runs: list[L3PassRun],
    excluded_sets: list[dict[str, Any]],
) -> str:
    if _failed_pass_run_ids(pass_runs):
        return PACKAGE_STATUS_REVIEW_ONLY
    if session.status == SESSION_STATUS_COMPLETED_WITH_WARNINGS:
        return PACKAGE_STATUS_COMPLETE_WITH_WARNINGS
    if excluded_sets:
        return PACKAGE_STATUS_COMPLETE_WITH_WARNINGS
    if _warning_pass_run_ids(pass_runs):
        return PACKAGE_STATUS_COMPLETE_WITH_WARNINGS
    return PACKAGE_STATUS_COMPLETE


def _reconciliation_status(package_status: str) -> str:
    if package_status == PACKAGE_STATUS_COMPLETE:
        return RECONCILIATION_STATUS_RECONCILED
    if package_status == PACKAGE_STATUS_COMPLETE_WITH_WARNINGS:
        return RECONCILIATION_STATUS_RECONCILED_WITH_WARNINGS
    return RECONCILIATION_STATUS_REVIEW_ONLY


def _artifact_inventory(artifacts: list[AnalysisArtifact]) -> list[dict[str, Any]]:
    return [
        {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "storage_ref": artifact.storage_ref,
            "summary": artifact.summary,
            "metadata_json": _json_clone(artifact.metadata_json or {}),
        }
        for artifact in artifacts
    ]


def _build_findings(
    *,
    session_id: str,
    pass_runs: list[L3PassRun],
    artifacts_by_run: dict[str, list[AnalysisArtifact]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for pass_run in pass_runs:
        if pass_run.status not in ACCEPTED_PASS_STATUSES:
            continue
        analysis_run_id = _analysis_run_id(pass_run)
        if analysis_run_id is None:
            continue
        findings.append(
            {
                "finding_id": _stable_hash(
                    {
                        "session_id": session_id,
                        "pass_run_id": pass_run.pass_run_id,
                        "finding_kind": "analysis_pass",
                    }
                ),
                "pass_run_id": pass_run.pass_run_id,
                "analysis_run_id": analysis_run_id,
                "analysis_set_id": pass_run.analysis_set_id,
                "pass_type": pass_run.pass_type,
                "selected_method_name": str((pass_run.summary_json or {}).get("selected_method_name") or "").strip(),
                "dataset_version_id": str((pass_run.summary_json or {}).get("dataset_version_id") or "").strip() or None,
                "artifact_inventory_json": _artifact_inventory(artifacts_by_run.get(analysis_run_id, [])),
                "input_payload_ref": pass_run.input_payload_ref,
                "output_payload_ref": pass_run.output_payload_ref,
            }
        )
    return findings


def _build_contradictions() -> list[dict[str, Any]]:
    return []


def _build_caveats(
    *,
    session_id: str,
    pass_runs: list[L3PassRun],
    excluded_sets: list[dict[str, Any]],
    caveats_by_run: dict[str, list[CaveatNote]],
) -> list[dict[str, Any]]:
    caveats: list[dict[str, Any]] = []
    for pass_run in pass_runs:
        analysis_run_id = _analysis_run_id(pass_run)
        if analysis_run_id:
            for caveat in caveats_by_run.get(analysis_run_id, []):
                caveats.append(
                    {
                        "caveat_id": _stable_hash(
                            {
                                "session_id": session_id,
                                "pass_run_id": pass_run.pass_run_id,
                                "caveat_type": caveat.caveat_type,
                                "message": caveat.message,
                            }
                        ),
                        "pass_run_id": pass_run.pass_run_id,
                        "analysis_run_id": analysis_run_id,
                        "caveat_type": caveat.caveat_type,
                        "severity": caveat.severity,
                        "message": caveat.message,
                    }
                )
        if pass_run.status == PASS_STATUS_FAILED:
            caveats.append(
                {
                    "caveat_id": _stable_hash(
                        {
                            "session_id": session_id,
                            "pass_run_id": pass_run.pass_run_id,
                            "caveat_type": "pass_failure",
                            "message": str((pass_run.summary_json or {}).get("error") or "").strip(),
                        }
                    ),
                    "pass_run_id": pass_run.pass_run_id,
                    "analysis_run_id": analysis_run_id,
                    "caveat_type": "pass_failure",
                    "severity": "high",
                    "message": str((pass_run.summary_json or {}).get("error") or "").strip(),
                }
            )

    for excluded in excluded_sets:
        analysis_set_id = str(excluded.get("analysis_set_id") or "").strip()
        reason_code = str(excluded.get("reason_code") or "excluded").strip()
        caveats.append(
            {
                "caveat_id": _stable_hash(
                    {
                        "session_id": session_id,
                        "analysis_set_id": analysis_set_id,
                        "reason_code": reason_code,
                    }
                ),
                "analysis_set_id": analysis_set_id,
                "analysis_modality": excluded.get("analysis_modality"),
                "caveat_type": "excluded_analysis_set",
                "severity": "medium",
                "message": f"Analysis set '{analysis_set_id}' was excluded from Gate C pass entry because {reason_code}.",
            }
        )
    return caveats


def _manifest_items_or_raise(manifest: L3SelectionManifest) -> list[dict[str, Any]]:
    manifest_json = manifest.manifest_json
    if not isinstance(manifest_json, dict):
        raise Layer3PackageEntryError(
            f"Layer 3 selection manifest '{manifest.selection_manifest_id}' is missing manifest_json.items required for Gate D package entry"
        )
    manifest_items = manifest_json.get("items")
    if not isinstance(manifest_items, list) or not manifest_items:
        raise Layer3PackageEntryError(
            f"Layer 3 selection manifest '{manifest.selection_manifest_id}' is missing manifest_json.items required for Gate D package entry"
        )
    return manifest_items


def _selection_and_source_summary(
    *,
    session: L3Session,
    manifest: L3SelectionManifest,
    descriptors: list[L3Descriptor],
    snapshots: list[L3MaterialSnapshot],
) -> dict[str, Any]:
    manifest_items = _manifest_items_or_raise(manifest)
    source_shape_counts = Counter(snapshot.source_shape for snapshot in snapshots)
    source_plane_counts = Counter(snapshot.source_plane for snapshot in snapshots)
    return {
        "selection_manifest_id": manifest.selection_manifest_id,
        "selection_hash": manifest.selection_hash,
        "source_plane_hints_json": _json_clone(manifest.source_plane_hints_json or {}),
        "manifest_item_count": len(manifest_items),
        "descriptor_count": len(descriptors),
        "material_snapshot_count": len(snapshots),
        "source_shape_counts_json": dict(sorted(source_shape_counts.items())),
        "source_plane_counts_json": dict(sorted(source_plane_counts.items())),
        "phase1a_loading_closure": _json_clone((session.summary_json or {}).get("phase1a_loading_closure") or {}),
        "material_snapshot_inventory_json": [
            {
                "material_snapshot_id": snapshot.material_snapshot_id,
                "descriptor_id": snapshot.descriptor_id,
                "source_plane": snapshot.source_plane,
                "source_shape": snapshot.source_shape,
                "payload_ref": snapshot.payload_ref,
                "payload_hash": snapshot.payload_hash,
                "source_identity_json": _json_clone(snapshot.source_identity_json or {}),
            }
            for snapshot in snapshots
        ],
    }


def _typing_and_set_summary(
    *,
    typings: list[L3TypingRecord],
    analysis_units: list[L3AnalysisUnit],
    analysis_groups: list[L3AnalysisGroup],
    analysis_sets: list[L3AnalysisSet],
    analysis_plan: L3AnalysisPlan,
    excluded_sets: list[dict[str, Any]],
) -> dict[str, Any]:
    modality_counts = Counter(typing.chosen_modality for typing in typings)
    set_type_counts = Counter(analysis_set.set_type for analysis_set in analysis_sets)
    return {
        "typing_record_count": len(typings),
        "analysis_unit_count": len(analysis_units),
        "analysis_group_count": len(analysis_groups),
        "analysis_set_count": len(analysis_sets),
        "chosen_modality_counts_json": dict(sorted(modality_counts.items())),
        "set_type_counts_json": dict(sorted(set_type_counts.items())),
        "admitted_analysis_set_ids_json": list(analysis_plan.analysis_set_ids_json or []),
        "excluded_sets_json": _json_clone(excluded_sets),
    }


def _pass_inventory_entry(pass_run: L3PassRun) -> dict[str, Any]:
    return {
        "pass_run_id": pass_run.pass_run_id,
        "analysis_set_id": pass_run.analysis_set_id,
        "pass_type": pass_run.pass_type,
        "engine_family": pass_run.engine_family,
        "status": pass_run.status,
        "selected_method_name": str((pass_run.summary_json or {}).get("selected_method_name") or "").strip() or None,
        "analysis_run_id": _analysis_run_id(pass_run),
        "input_payload_ref": pass_run.input_payload_ref,
        "output_payload_ref": pass_run.output_payload_ref,
        "dataset_version_id": str((pass_run.summary_json or {}).get("dataset_version_id") or "").strip() or None,
        "artifact_refs_json": list((pass_run.summary_json or {}).get("artifact_refs_json") or []),
    }


def _pass_summary(
    *,
    session: L3Session,
    analysis_plan: L3AnalysisPlan,
    pass_runs: list[L3PassRun],
    excluded_sets: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "plan_status": analysis_plan.status,
        "approved_by_operator": analysis_plan.approved_by_operator,
        "plan_json": _json_clone(analysis_plan.plan_json or {}),
        "session_pass_entry_summary": _json_clone(_pass_entry_summary(session)),
        "pass_run_inventory_json": [_pass_inventory_entry(pass_run) for pass_run in pass_runs],
        "accepted_pass_run_ids_json": _accepted_pass_run_ids(pass_runs),
        "warning_pass_run_ids_json": _warning_pass_run_ids(pass_runs),
        "failed_pass_run_ids_json": _failed_pass_run_ids(pass_runs),
        "excluded_sets_json": _json_clone(excluded_sets),
    }


def _trace_payload_refs(
    *,
    snapshots: list[L3MaterialSnapshot],
    pass_runs: list[L3PassRun],
) -> list[str]:
    refs = {snapshot.payload_ref for snapshot in snapshots if str(snapshot.payload_ref or "").strip()}
    refs.update(pass_run.input_payload_ref for pass_run in pass_runs if str(pass_run.input_payload_ref or "").strip())
    refs.update(pass_run.output_payload_ref for pass_run in pass_runs if str(pass_run.output_payload_ref or "").strip())
    return sorted(refs)


def _package_header(
    *,
    session_id: str,
    package_kind: str,
    package_status: str,
    canonical_package_key: str | None = None,
    source_gate: str = SOURCE_GATE_D_PACKAGE_FREEZE,
) -> dict[str, Any]:
    header = {
        "schema_id": PACKAGE_SCHEMA_IDS[package_kind],
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_key": _package_key(session_id=session_id, package_kind=package_kind),
        "package_kind": package_kind,
        "package_status": package_status,
        "session_id": session_id,
        "source_gate": source_gate,
    }
    if canonical_package_key:
        header["canonical_package_key"] = canonical_package_key
    return header


def _handoff_status(*, package_status: str) -> dict[str, Any]:
    return {
        "status": PACKAGE_STATUS_HANDOFF_BLOCKED,
        "canonical_package_status": package_status,
        "aps_handoff_admitted": False,
        "compatibility_notes_json": [
            "canonical_internal is the source of truth",
            "user_facing and review_facing projections are admitted",
            "aps_handoff remains deferred by 08_GATED_PACKAGE_FREEZE",
        ],
    }


def _canonical_payload(
    *,
    session: L3Session,
    manifest: L3SelectionManifest,
    descriptors: list[L3Descriptor],
    snapshots: list[L3MaterialSnapshot],
    typings: list[L3TypingRecord],
    analysis_units: list[L3AnalysisUnit],
    analysis_groups: list[L3AnalysisGroup],
    analysis_sets: list[L3AnalysisSet],
    analysis_plan: L3AnalysisPlan,
    pass_runs: list[L3PassRun],
    excluded_sets: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    caveats: list[dict[str, Any]],
    package_status: str,
) -> dict[str, Any]:
    return {
        "package_header": _package_header(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_CANONICAL_INTERNAL,
            package_status=package_status,
        ),
        "selection_and_source_summary": _selection_and_source_summary(
            session=session,
            manifest=manifest,
            descriptors=descriptors,
            snapshots=snapshots,
        ),
        "typing_and_set_summary": _typing_and_set_summary(
            typings=typings,
            analysis_units=analysis_units,
            analysis_groups=analysis_groups,
            analysis_sets=analysis_sets,
            analysis_plan=analysis_plan,
            excluded_sets=excluded_sets,
        ),
        "pass_summary": _pass_summary(
            session=session,
            analysis_plan=analysis_plan,
            pass_runs=pass_runs,
            excluded_sets=excluded_sets,
        ),
        "findings": _json_clone(findings),
        "contradictions": _json_clone(contradictions),
        "caveats": _json_clone(caveats),
        "consumer_projection_summary": {
            "derived_package_kinds_json": [
                PACKAGE_KIND_USER_FACING,
                PACKAGE_KIND_REVIEW_FACING,
            ],
            "package_status": package_status,
            "excluded_set_count": len(excluded_sets),
            "warning_pass_run_ids_json": _warning_pass_run_ids(pass_runs),
            "failed_pass_run_ids_json": _failed_pass_run_ids(pass_runs),
        },
        "handoff_status": _handoff_status(package_status=package_status),
    }


def _user_facing_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    simplified: list[dict[str, Any]] = []
    for finding in findings:
        artifacts = [dict(item or {}) for item in list(finding.get("artifact_inventory_json") or []) if isinstance(item, dict)]
        simplified.append(
            {
                "finding_id": finding.get("finding_id"),
                "pass_run_id": finding.get("pass_run_id"),
                "selected_method_name": finding.get("selected_method_name"),
                "dataset_version_id": finding.get("dataset_version_id"),
                "artifact_refs_json": [artifact.get("storage_ref") for artifact in artifacts if artifact.get("storage_ref")],
                "artifact_types_json": [artifact.get("artifact_type") for artifact in artifacts if artifact.get("artifact_type")],
                "artifact_summaries_json": [artifact.get("summary") for artifact in artifacts if artifact.get("summary")],
            }
        )
    return simplified


def _severity_counts(caveats: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(caveat.get("severity") or "unknown") for caveat in caveats)
    return dict(sorted(counts.items()))


def _user_facing_payload(
    *,
    session: L3Session,
    canonical_payload: dict[str, Any],
    package_status: str,
    excluded_sets: list[dict[str, Any]],
    pass_runs: list[L3PassRun],
    contradictions: list[dict[str, Any]],
    caveats: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical_package_key = canonical_payload["package_header"]["package_key"]
    return {
        "package_header": _package_header(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_USER_FACING,
            package_status=package_status,
            canonical_package_key=canonical_package_key,
        ),
        "session_summary": {
            "session_id": session.session_id,
            "session_status": session.status,
            "selection_manifest_id": canonical_payload["selection_and_source_summary"]["selection_manifest_id"],
            "admitted_pass_count": len(_accepted_pass_run_ids(pass_runs)),
        },
        "accepted_findings": _user_facing_findings(list(canonical_payload.get("findings") or [])),
        "contradictions_summary": {
            "count": len(contradictions),
            "items": _json_clone(contradictions),
        },
        "caveats_summary": {
            "count": len(caveats),
            "severity_counts_json": _severity_counts(caveats),
            "items": _json_clone(caveats),
        },
        "provisional_or_warning_summary": {
            "package_status": package_status,
            "excluded_set_count": len(excluded_sets),
            "warning_pass_run_ids_json": _warning_pass_run_ids(pass_runs),
            "failed_pass_run_ids_json": _failed_pass_run_ids(pass_runs),
            "is_provisional": package_status != PACKAGE_STATUS_COMPLETE,
        },
    }


def _review_facing_payload(
    *,
    session: L3Session,
    canonical_payload: dict[str, Any],
    package_status: str,
    pass_runs: list[L3PassRun],
    excluded_sets: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    caveats: list[dict[str, Any]],
    trace_payload_refs: list[str],
) -> dict[str, Any]:
    canonical_package_key = canonical_payload["package_header"]["package_key"]
    return {
        "package_header": _package_header(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_REVIEW_FACING,
            package_status=package_status,
            canonical_package_key=canonical_package_key,
        ),
        "session_summary": {
            "session_id": session.session_id,
            "session_status": session.status,
            "selection_manifest_id": canonical_payload["selection_and_source_summary"]["selection_manifest_id"],
            "package_status": package_status,
        },
        "pass_provenance": _json_clone(canonical_payload["pass_summary"]),
        "accepted_inventory": _json_clone(canonical_payload.get("findings") or []),
        "warning_failure_inventory": {
            "warning_pass_run_ids_json": _warning_pass_run_ids(pass_runs),
            "failed_pass_run_ids_json": _failed_pass_run_ids(pass_runs),
            "excluded_sets_json": _json_clone(excluded_sets),
        },
        "contradictions": _json_clone(contradictions),
        "caveats": _json_clone(caveats),
        "trace_payload_refs_json": trace_payload_refs,
    }


def _build_reconciliation_summary(
    *,
    analysis_plan: L3AnalysisPlan,
    pass_runs: list[L3PassRun],
    excluded_sets: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    caveats: list[dict[str, Any]],
    package_status: str,
) -> dict[str, Any]:
    return {
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "pass_run_ids_json": [pass_run.pass_run_id for pass_run in pass_runs],
        "accepted_pass_run_ids_json": _accepted_pass_run_ids(pass_runs),
        "warning_pass_run_ids_json": _warning_pass_run_ids(pass_runs),
        "failed_pass_run_ids_json": _failed_pass_run_ids(pass_runs),
        "excluded_set_count": len(excluded_sets),
        "findings_json": _json_clone(findings),
        "contradictions_json": _json_clone(contradictions),
        "caveats_json": _json_clone(caveats),
        "package_status": package_status,
        "source_gate": SOURCE_GATE_D_PACKAGE_FREEZE,
    }


def _output_package_summary(
    *,
    package_kind: str,
    payload: dict[str, Any],
    package_status: str,
    findings: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    caveats: list[dict[str, Any]],
    source_gate: str = SOURCE_GATE_D_PACKAGE_FREEZE,
) -> dict[str, Any]:
    return {
        "schema_id": payload["package_header"]["schema_id"],
        "package_key": payload["package_header"]["package_key"],
        "package_status": package_status,
        "source_gate": source_gate,
        "package_kind": package_kind,
        "section_keys_json": sorted(payload.keys()),
        "finding_count": len(findings),
        "contradiction_count": len(contradictions),
        "caveat_count": len(caveats),
    }


def _workbench_package_status(pass_run: L3PassRun) -> str:
    if pass_run.status == PASS_STATUS_FAILED:
        return PACKAGE_STATUS_REVIEW_ONLY
    if pass_run.status == PASS_STATUS_COMPLETED_WITH_WARNINGS:
        return PACKAGE_STATUS_COMPLETE_WITH_WARNINGS
    return PACKAGE_STATUS_COMPLETE


def _workbench_artifact_inventory(output_metadata_summary: dict[str, Any]) -> list[dict[str, Any]]:
    refs = list(output_metadata_summary.get("artifact_refs_json") or output_metadata_summary.get("artifact_refs") or [])
    types = list(output_metadata_summary.get("artifact_types_json") or output_metadata_summary.get("artifact_types") or [])
    inventory: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        inventory.append(
            {
                "artifact_index": index,
                "storage_ref": ref,
                "artifact_type": types[index] if index < len(types) else None,
            }
        )
    return inventory


def _workbench_authority_basis_hash(authority_basis: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json_bytes(authority_basis)).hexdigest()


def _existing_workbench_package_result(
    db: Session,
    *,
    session_id: str,
    authority_basis_hash: str,
    client_request_id: str,
) -> Layer3PackageEntryResult | None:
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .one_or_none()
    )
    packages = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    if reconciliation is None and not packages:
        return None
    if reconciliation is None or len(packages) != 3:
        raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' has partial package construction state")
    packages_by_kind = {package.package_kind: package for package in packages}
    expected = (
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    )
    if set(packages_by_kind) != set(expected):
        raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' has unexpected package kinds")
    summary = reconciliation.summary_json or {}
    commit_summary = summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' already has non-workbench package state")
    if (
        commit_summary.get("authority_basis_hash") == authority_basis_hash
        and commit_summary.get("client_request_id") == client_request_id
    ):
        return Layer3PackageEntryResult(
            reconciliation_record=reconciliation,
            output_packages=tuple(packages_by_kind[package_kind] for package_kind in expected),
            replayed=True,
        )
    raise Layer3PackageEntryError(f"Layer 3 session '{session_id}' already has package construction state")


def materialize_workbench_package_commit(
    db: Session,
    *,
    session: L3Session,
    analysis_plan: L3AnalysisPlan,
    pass_run: L3PassRun,
    preview_id: str,
    preview_hash: str,
    result_review_state: dict[str, Any],
    package_review_preview_hash: str,
    output_metadata_summary: dict[str, Any],
    client_request_id: str,
    source_gate: str = SOURCE_WORKBENCH_PACKAGE_CONSTRUCTION_FREEZE,
    package_review_submit_enabled: bool = True,
    downstream_unavailable: list[str] | tuple[str, ...] | None = None,
    authority_schema_id: str = "layer3.workbench_package_construction_authority.v1",
    authority_basis_extra: dict[str, Any] | None = None,
    package_payload_extras_by_kind: dict[str, dict[str, Any]] | None = None,
) -> Layer3PackageEntryResult:
    unavailable = list(downstream_unavailable or ["handoff", "export"])
    authority_basis = {
        "schema_id": authority_schema_id,
        "client_request_id": client_request_id,
        "session_id": session.session_id,
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "analysis_run_id": output_metadata_summary.get("analysis_run_id"),
        "result_review_record_ref": result_review_state.get("review_record_ref"),
        "package_review_preview_hash": package_review_preview_hash,
        "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
        "unresolved_trace_count": int(result_review_state.get("unresolved_trace_count") or 0),
        "source_gate": source_gate,
    }
    if authority_basis_extra:
        authority_basis.update(_json_clone(authority_basis_extra))
    authority_basis_hash = _workbench_authority_basis_hash(authority_basis)
    existing = _existing_workbench_package_result(
        db,
        session_id=session.session_id,
        authority_basis_hash=authority_basis_hash,
        client_request_id=client_request_id,
    )
    if existing is not None:
        return existing

    package_status = _workbench_package_status(pass_run)
    trace_summary = _json_clone(result_review_state.get("trace_summary") or {})
    reviewed_items = _json_clone(result_review_state.get("reviewed_output_items") or [])
    artifact_inventory = _workbench_artifact_inventory(output_metadata_summary)
    workbench_summary = {
        "authority_basis": authority_basis,
        "authority_basis_hash": authority_basis_hash,
        "review_state": result_review_state.get("review_state"),
        "operator_decision": result_review_state.get("operator_decision"),
        "trace_summary": trace_summary,
        "reviewed_output_items": reviewed_items,
        "output_metadata_summary": _json_clone(output_metadata_summary),
        "package_review_submit_enabled": package_review_submit_enabled,
        "handoff_enabled": False,
        "downstream_unavailable": unavailable,
    }
    canonical_payload = {
        "package_header": _package_header(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_CANONICAL_INTERNAL,
            package_status=package_status,
            source_gate=source_gate,
        ),
        "workbench_authority_summary": _json_clone(workbench_summary),
        "approved_plan_summary": {
            "analysis_plan_id": analysis_plan.analysis_plan_id,
            "approved_by_operator": analysis_plan.approved_by_operator,
            "approved_at": analysis_plan.approved_at.isoformat() if analysis_plan.approved_at else None,
        },
        "selected_pass_result_summary": {
            "pass_run_id": pass_run.pass_run_id,
            "pass_run_status": pass_run.status,
            "analysis_run_id": output_metadata_summary.get("analysis_run_id"),
            "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
            "artifact_inventory_json": artifact_inventory,
        },
        "handoff_status": _handoff_status(package_status=package_status),
    }
    canonical_key = canonical_payload["package_header"]["package_key"]
    user_facing_payload = {
        "package_header": _package_header(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_USER_FACING,
            package_status=package_status,
            canonical_package_key=canonical_key,
            source_gate=source_gate,
        ),
        "session_summary": {
            "session_id": session.session_id,
            "analysis_plan_id": analysis_plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "package_status": package_status,
        },
        "result_summary": _json_clone(canonical_payload["selected_pass_result_summary"]),
        "review_summary": {
            "operator_decision": result_review_state.get("operator_decision"),
            "review_record_ref": result_review_state.get("review_record_ref"),
            "unresolved_trace_count": int(result_review_state.get("unresolved_trace_count") or 0),
        },
        "downstream_unavailable": unavailable,
    }
    review_facing_payload = {
        "package_header": _package_header(
            session_id=session.session_id,
            package_kind=PACKAGE_KIND_REVIEW_FACING,
            package_status=package_status,
            canonical_package_key=canonical_key,
            source_gate=source_gate,
        ),
        "workbench_authority_summary": _json_clone(workbench_summary),
        "trace_summary": trace_summary,
        "reviewed_output_items": reviewed_items,
        "artifact_inventory_json": artifact_inventory,
        "owner_service_notes_json": [
            "constructed by workbench package-construction helper",
            "handoff remains deferred",
        ],
    }
    package_payloads = {
        PACKAGE_KIND_CANONICAL_INTERNAL: canonical_payload,
        PACKAGE_KIND_USER_FACING: user_facing_payload,
        PACKAGE_KIND_REVIEW_FACING: review_facing_payload,
    }
    for package_kind, extra in (package_payload_extras_by_kind or {}).items():
        if package_kind in package_payloads and isinstance(extra, dict):
            package_payloads[package_kind].update(_json_clone(extra))
    reconciliation_summary = {
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "pass_run_ids_json": [pass_run.pass_run_id],
        "accepted_pass_run_ids_json": [pass_run.pass_run_id] if pass_run.status in ACCEPTED_PASS_STATUSES else [],
        "warning_pass_run_ids_json": [pass_run.pass_run_id] if pass_run.status == PASS_STATUS_COMPLETED_WITH_WARNINGS else [],
        "failed_pass_run_ids_json": [pass_run.pass_run_id] if pass_run.status == PASS_STATUS_FAILED else [],
        "package_status": package_status,
        "source_gate": source_gate,
        "workbench_package_commit": {
            "schema_id": "layer3.workbench_package_commit_summary.v1",
            "client_request_id": client_request_id,
            "authority_basis": _json_clone(authority_basis),
            "authority_basis_hash": authority_basis_hash,
            "package_review_preview_hash": package_review_preview_hash,
            "result_review_record_ref": result_review_state.get("review_record_ref"),
            "analysis_run_id": authority_basis.get("analysis_run_id"),
            "pass_type": authority_basis.get("pass_type"),
            "pass_scope": authority_basis.get("pass_scope"),
            "method": authority_basis.get("method"),
            "source_gate": authority_basis.get("source_gate"),
            "package_construction_source_gate": source_gate,
            "source_shape": authority_basis.get("source_shape"),
            "source_dataset_version_ids": _json_clone(authority_basis.get("source_dataset_version_ids") or []),
            "content_id": authority_basis.get("content_id"),
            "content_contract_id": authority_basis.get("content_contract_id"),
            "chunking_contract_id": authority_basis.get("chunking_contract_id"),
            "material_snapshot_id": authority_basis.get("material_snapshot_id"),
            "analysis_unit_id": authority_basis.get("analysis_unit_id"),
            "analysis_set_id": authority_basis.get("analysis_set_id"),
            "source_intake_record_id": authority_basis.get("source_intake_record_id"),
            "candidate_id": authority_basis.get("candidate_id"),
            "output_payload_ref": authority_basis.get("output_payload_ref"),
            "output_payload_hash": authority_basis.get("output_payload_hash"),
            "package_review_submit_enabled": package_review_submit_enabled,
            "handoff_enabled": False,
            "downstream_unavailable": unavailable,
        },
    }
    reconciliation_record = L3ReconciliationRecord(
        reconciliation_record_id=uuid_str(),
        session_id=session.session_id,
        status=_reconciliation_status(package_status),
        summary_json=reconciliation_summary,
    )
    db.add(reconciliation_record)
    db.flush()

    package_rows: list[L3OutputPackage] = []
    for package_kind in (
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    ):
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
                reconciliation_record_id=reconciliation_record.reconciliation_record_id,
                package_kind=package_kind,
                status=package_status,
                payload_ref=payload_ref,
                payload_hash=payload_hash,
                summary_json=_output_package_summary(
                    package_kind=package_kind,
                    payload=payload,
                    package_status=package_status,
                    findings=artifact_inventory,
                    contradictions=[],
                    caveats=[],
                    source_gate=source_gate,
                ),
            )
        )
    db.add_all(package_rows)
    db.flush()
    construction_basis_hash = _workbench_authority_basis_hash(
        {
            **authority_basis,
            "package_kinds": [package.package_kind for package in package_rows],
            "payload_refs": [package.payload_ref for package in package_rows],
            "payload_hashes": [package.payload_hash for package in package_rows],
        }
    )
    reconciliation_summary["workbench_package_commit"]["construction_basis_hash"] = construction_basis_hash
    reconciliation_record.summary_json = reconciliation_summary
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


def materialize_package_entry(db: Session, *, session_id: str) -> Layer3PackageEntryResult:
    session = _load_session_or_raise(db, session_id=session_id)
    _ensure_session_not_yet_packaged(db, session_id=session_id)

    manifest, descriptors, snapshots = _load_selection_context(db, session_id=session.session_id)
    typings, analysis_units, analysis_groups, analysis_sets = _load_typing_context(
        db,
        session_id=session.session_id,
    )
    analysis_plan, pass_runs, excluded_sets = _load_plan_and_pass_runs(db, session=session)
    analysis_runs_by_id = _validate_pass_provenance(db, pass_runs=pass_runs)
    analysis_run_ids = sorted(analysis_runs_by_id)
    artifacts_by_run = _load_artifacts_by_run(db, analysis_run_ids=analysis_run_ids)
    caveats_by_run = _load_caveats_by_run(db, analysis_run_ids=analysis_run_ids)

    findings = _build_findings(
        session_id=session.session_id,
        pass_runs=pass_runs,
        artifacts_by_run=artifacts_by_run,
    )
    contradictions = _build_contradictions()
    caveats = _build_caveats(
        session_id=session.session_id,
        pass_runs=pass_runs,
        excluded_sets=excluded_sets,
        caveats_by_run=caveats_by_run,
    )
    package_status = _package_status(
        session=session,
        pass_runs=pass_runs,
        excluded_sets=excluded_sets,
    )

    reconciliation_summary = _build_reconciliation_summary(
        analysis_plan=analysis_plan,
        pass_runs=pass_runs,
        excluded_sets=excluded_sets,
        findings=findings,
        contradictions=contradictions,
        caveats=caveats,
        package_status=package_status,
    )
    canonical_payload = _canonical_payload(
        session=session,
        manifest=manifest,
        descriptors=descriptors,
        snapshots=snapshots,
        typings=typings,
        analysis_units=analysis_units,
        analysis_groups=analysis_groups,
        analysis_sets=analysis_sets,
        analysis_plan=analysis_plan,
        pass_runs=pass_runs,
        excluded_sets=excluded_sets,
        findings=findings,
        contradictions=contradictions,
        caveats=caveats,
        package_status=package_status,
    )
    trace_payload_refs = _trace_payload_refs(snapshots=snapshots, pass_runs=pass_runs)
    user_facing_payload = _user_facing_payload(
        session=session,
        canonical_payload=canonical_payload,
        package_status=package_status,
        excluded_sets=excluded_sets,
        pass_runs=pass_runs,
        contradictions=contradictions,
        caveats=caveats,
    )
    review_facing_payload = _review_facing_payload(
        session=session,
        canonical_payload=canonical_payload,
        package_status=package_status,
        pass_runs=pass_runs,
        excluded_sets=excluded_sets,
        contradictions=contradictions,
        caveats=caveats,
        trace_payload_refs=trace_payload_refs,
    )

    reconciliation_record = L3ReconciliationRecord(
        reconciliation_record_id=uuid_str(),
        session_id=session.session_id,
        status=_reconciliation_status(package_status),
        summary_json=reconciliation_summary,
    )
    db.add(reconciliation_record)
    db.flush()

    package_rows: list[L3OutputPackage] = []
    for package_kind, payload in (
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_USER_FACING, user_facing_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_facing_payload),
    ):
        payload_ref, payload_hash = _persist_package_payload(
            session_id=session.session_id,
            package_kind=package_kind,
            payload=payload,
        )
        package_rows.append(
            L3OutputPackage(
                output_package_id=uuid_str(),
                session_id=session.session_id,
                reconciliation_record_id=reconciliation_record.reconciliation_record_id,
                package_kind=package_kind,
                status=package_status,
                payload_ref=payload_ref,
                payload_hash=payload_hash,
                summary_json=_output_package_summary(
                    package_kind=package_kind,
                    payload=payload,
                    package_status=package_status,
                    findings=findings,
                    contradictions=contradictions,
                    caveats=caveats,
                ),
            )
        )
    db.add_all(package_rows)
    db.flush()

    return Layer3PackageEntryResult(
        reconciliation_record=reconciliation_record,
        output_packages=tuple(package_rows),
    )
