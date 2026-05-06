from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.models import L3PassRun


def output_metadata_summary(pass_run: L3PassRun) -> tuple[dict[str, Any] | None, str | None]:
    output_ref = str(pass_run.output_payload_ref or "").strip()
    if not output_ref:
        return None, "output_payload_ref_missing"
    output_path = Path(output_ref)
    if not output_path.exists() or not output_path.is_file():
        return None, "output_metadata_file_missing"
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "output_metadata_unreadable"
    if not isinstance(payload, dict):
        return None, "output_metadata_malformed"
    artifact_refs = payload.get("artifact_refs_json")
    artifact_types = payload.get("artifact_types_json")
    return (
        {
            "present": True,
            "readable": True,
            "output_payload_ref": output_ref,
            "analysis_run_id": payload.get("analysis_run_id"),
            "analysis_set_id": payload.get("analysis_set_id"),
            "dataset_version_id": payload.get("dataset_version_id"),
            "selected_method_name": payload.get("selected_method_name"),
            "artifact_count": len(artifact_refs) if isinstance(artifact_refs, list) else 0,
            "artifact_refs": list(artifact_refs or []) if isinstance(artifact_refs, list) else [],
            "artifact_types": list(artifact_types or []) if isinstance(artifact_types, list) else [],
            "source_gate": payload.get("source_gate"),
            "pass_scope": payload.get("pass_scope"),
            "source_dataset_version_ids": (
                list(payload.get("source_dataset_version_ids_json"))
                if isinstance(payload.get("source_dataset_version_ids_json"), list)
                else None
            ),
            "cohort_shape": payload.get("cohort_shape"),
            "requested_method_name": payload.get("requested_method_name"),
            "requested_method_source": payload.get("requested_method_source"),
            "engine_family": payload.get("engine_family"),
            "pass_type": payload.get("pass_type"),
            "source_shape": payload.get("source_shape"),
            "material_snapshot_id": payload.get("material_snapshot_id"),
            "analysis_unit_id": payload.get("analysis_unit_id"),
            "content_id": (
                payload.get("content_id")
                or (
                    payload.get("document_identity", {}).get("content_id")
                    if isinstance(payload.get("document_identity"), dict)
                    else None
                )
            ),
            "chunk_ids": (
                list(payload.get("chunk_summary", {}).get("chunk_ids"))
                if isinstance(payload.get("chunk_summary"), dict)
                and isinstance(payload.get("chunk_summary", {}).get("chunk_ids"), list)
                else None
            ),
            "chunk_hashes": (
                list(payload.get("chunk_summary", {}).get("chunk_hashes"))
                if isinstance(payload.get("chunk_summary"), dict)
                and isinstance(payload.get("chunk_summary", {}).get("chunk_hashes"), list)
                else None
            ),
        },
        None,
    )
