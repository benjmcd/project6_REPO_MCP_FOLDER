from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import DatasetSourceProvenance
from test_layer3_api import client as client
from test_layer3_bounded_e2e import Layer3ApiDriver
from test_layer3_pass_entry import _seed_timeseries_dataset_version


def _seed_dataset_version(db: Any, tmp_path: Path, *, dataset_version_id: str) -> None:
    _seed_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id=f"dataset-{dataset_version_id}",
        dataset_version_id=dataset_version_id,
    )


def _seed_provenance(
    db: Any,
    *,
    dataset_version_id: str,
    source_system: str,
    source_artifact_key: str,
    created_at: datetime,
    source_reference_json: dict[str, Any] | None = None,
) -> None:
    db.add(
        DatasetSourceProvenance(
            dataset_version_id=dataset_version_id,
            source_system=source_system,
            source_mode="materialized_dataset_version",
            source_artifact_key=source_artifact_key,
            source_reference_json=source_reference_json or {},
            created_at=created_at,
        )
    )


def _dataset_version_material_preview(client: Any, *, dataset_version_ids: list[str]) -> dict[str, Any]:
    driver = Layer3ApiDriver(client)
    preflight = driver.post_ok(
        "/api/v1/layer3/preflight",
        {
            "client_request_id": "admission-map-pins-preflight",
            "natural_language_intent": "Pin current dataset-version admission map labels.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        },
    )
    source = driver.post_ok(
        "/api/v1/layer3/source-preview",
        {
            "client_request_id": "admission-map-pins-source-preview",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        },
    )
    return driver.post_ok(
        "/api/v1/layer3/material-preview",
        {
            "client_request_id": "admission-map-pins-material-preview",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [
                candidate["source_candidate_id"] for candidate in source["source_candidates"]
            ],
            "dataset_version_ids": dataset_version_ids,
            "query_basis": {
                "terms": ["admission-map", "dataset-version"],
                "filters": {"dataset_version_ids": dataset_version_ids},
            },
        },
    )


def _dataset_version_candidate(material: dict[str, Any], *, dataset_version_id: str) -> dict[str, Any]:
    for candidate in material["material_candidates"]:
        if (
            candidate["source_class"] == "dataset_version"
            and candidate["source_identity"]["dataset_version_id"] == dataset_version_id
        ):
            return candidate
    raise AssertionError(f"dataset_version candidate not found: {dataset_version_id}")


def test_layer3_admission_map_provenanceless_fallback_pins_current_label(client: Any, tmp_path: Path) -> None:
    dataset_version_id = "dv-admission-map-provenanceless"
    with client.layer3_session_factory() as db:
        _seed_dataset_version(db, tmp_path, dataset_version_id=dataset_version_id)
        db.commit()

    material = _dataset_version_material_preview(client, dataset_version_ids=[dataset_version_id])
    candidate = _dataset_version_candidate(material, dataset_version_id=dataset_version_id)
    provenance = candidate["source_provenance"]

    assert provenance["source_admission_state"] == "admitted_dataset_version"
    assert provenance["source_family"] == "dataset_version"
    assert provenance["aps_source_provenance"] == []
    assert provenance["aps_derived"] is False


def test_layer3_admission_map_newest_row_only_gate_pins_current_behavior(client: Any, tmp_path: Path) -> None:
    dataset_version_id = "dv-admission-map-newest-row"
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = older + timedelta(minutes=1)
    with client.layer3_session_factory() as db:
        _seed_dataset_version(db, tmp_path, dataset_version_id=dataset_version_id)
        _seed_provenance(
            db,
            dataset_version_id=dataset_version_id,
            source_system="some_non_admitted_source",
            source_artifact_key="older-non-admitted",
            created_at=older,
        )
        _seed_provenance(
            db,
            dataset_version_id=dataset_version_id,
            source_system="nrc_adams_aps",
            source_artifact_key="newer-admitted",
            created_at=newer,
        )
        db.commit()

    material = _dataset_version_material_preview(client, dataset_version_ids=[dataset_version_id])
    candidate = _dataset_version_candidate(material, dataset_version_id=dataset_version_id)
    aps_provenance = candidate["source_provenance"]["aps_source_provenance"]

    assert len(aps_provenance) == 1
    assert aps_provenance[0]["source_system"] == "nrc_adams_aps"
    assert aps_provenance[0]["source_artifact_key"] == "newer-admitted"


def test_layer3_admission_map_unknown_parser_family_pins_admitted_label(client: Any, tmp_path: Path) -> None:
    dataset_version_id = "dv-admission-map-unknown-parser"
    with client.layer3_session_factory() as db:
        _seed_dataset_version(db, tmp_path, dataset_version_id=dataset_version_id)
        _seed_provenance(
            db,
            dataset_version_id=dataset_version_id,
            source_system="nrc_adams_aps",
            source_artifact_key="unknown-parser-family",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_reference_json={"parser_family": "totally_unrecognized_parser_family_v1"},
        )
        db.commit()

    material = _dataset_version_material_preview(client, dataset_version_ids=[dataset_version_id])
    candidate = _dataset_version_candidate(material, dataset_version_id=dataset_version_id)
    provenance = candidate["source_provenance"]

    assert provenance["source_family"] == "unknown_aps_dataset_version"
    assert provenance["source_admission_state"] == "admitted_materialized_dataset_version"
