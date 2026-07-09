from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import (
    layer3_artifact_ingestion_facade as facade,
    layer3_workbench,
    nrc_aps_artifact_ingestion,
)

FIVE_CONTRACT_SYMBOLS = (
    "validate_target_artifact_payload",
    "APS_ARTIFACT_INGESTION_SCHEMA_VERSION",
    "APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID",
    "APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID",
    "APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE",
)


def _valid_unsupported_media_target_payload() -> dict:
    return nrc_aps_artifact_ingestion.build_target_artifact_payload(
        run_id="run-schema-gate",
        target_id="target-schema-gate",
        accession_number="ML123",
        pipeline_mode=nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_DOWNLOAD_ONLY,
        artifact_required_for_target_success=True,
        outcome_status="artifact_refused",
        target_success=False,
        evidence={
            "source": "unit-test",
            "discovery_ref": "discovery-ref",
            "selection_ref": "selection-ref",
        },
        source_metadata_ref="metadata-ref",
        failure={
            "code": nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE,
            "evidence": {
                "declared_content_type": "application/octet-stream",
                "sniffed_content_type": "application/octet-stream",
                "detected_content_type": "application/octet-stream",
                "media_detection_status": "unsupported",
                "allowed_content_types": ["application/pdf"],
                "blob_ref": "blob-ref",
            },
        },
    )


def test_target_payload_validation_gate_behavior_unchanged() -> None:
    valid = _valid_unsupported_media_target_payload()

    assert layer3_workbench._valid_aps_target_artifact_payload(valid) is True
    assert layer3_workbench._valid_aps_target_artifact_payload(valid | {"schema_id": "wrong.schema"}) is False

    malformed_failure = dict(valid)
    malformed_failure["failure"] = "not-a-dict"
    assert layer3_workbench._valid_aps_target_artifact_payload(malformed_failure) is False


def test_run_schema_version_gate_and_int_coercion_preserved() -> None:
    version = nrc_aps_artifact_ingestion.APS_ARTIFACT_INGESTION_SCHEMA_VERSION
    matches = layer3_workbench._aps_artifact_schema_version_matches

    assert matches({"schema_version": version}) is True
    assert matches({"schema_version": version + 1}) is False
    assert matches({}) is False
    assert matches({"schema_version": None}) is False
    assert matches({"schema_version": "bad"}) is False

    # Latent coercion pinned as current behavior, not endorsed. Document and
    # preserve for this lane; do not fix while proving the facade is neutral.
    assert matches({"schema_version": float(version) + 0.9}) is True
    assert matches({"schema_version": True}) is True


def test_target_schema_id_gate_returns_none_on_mismatch() -> None:
    # This guard is shadowed by public target-payload validation for real
    # non-empty mismatches, so the direct private call is the narrow in-fence pin.
    assert (
        layer3_workbench._aps_refused_artifact_trace(
            run=None,
            run_artifact_ref="run-ref",
            target_artifact_ref="target-ref",
            target_payload={"schema_id": "wrong.schema"},
        )
        is None
    )


def test_consumer_run_schema_id_binding_resolves_identically() -> None:
    # The RUN schema-id read is inline in aps_refused_artifact_traces. Pin the
    # consumer binding by identity rather than widening the fence for seeding.
    for name in FIVE_CONTRACT_SYMBOLS:
        assert getattr(layer3_workbench.nrc_aps_artifact_ingestion, name) is getattr(
            nrc_aps_artifact_ingestion,
            name,
        )


def test_facade_reexports_preserve_object_identity() -> None:
    for name in FIVE_CONTRACT_SYMBOLS:
        assert getattr(facade, name) is getattr(nrc_aps_artifact_ingestion, name)
        assert name in facade.__all__

    assert set(facade.ARTIFACT_INGESTION_PROVIDERS) == {"nrc_aps"}
    assert facade.ARTIFACT_INGESTION_PROVIDERS["nrc_aps"] is nrc_aps_artifact_ingestion


def test_facade_is_sole_layer3_service_importer_of_nrc_aps_artifact_ingestion() -> None:
    direct_import = "from app.services import nrc_aps_artifact_ingestion"
    facade_import = "from app.services import layer3_artifact_ingestion_facade as nrc_aps_artifact_ingestion"
    services = Path(__file__).resolve().parents[1] / "app" / "services"

    def has_exact_import_line(text: str) -> bool:
        return any(line.strip() == direct_import for line in text.splitlines())

    importers = [
        path.name
        for path in sorted(services.glob("layer3_*.py"))
        if has_exact_import_line(path.read_text(encoding="utf-8"))
    ]
    assert importers == ["layer3_artifact_ingestion_facade.py"]

    workbench = (services / "layer3_workbench.py").read_text(encoding="utf-8")
    assert not has_exact_import_line(workbench)
    assert any(line.strip() == facade_import for line in workbench.splitlines())
