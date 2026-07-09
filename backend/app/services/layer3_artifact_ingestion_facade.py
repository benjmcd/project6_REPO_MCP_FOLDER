"""Neutral facade for the NRC APS artifact-ingestion contract (Layer 3 admission spine, Phase 2).

Contract
--------
Single indirection seam Layer 3 consumers use to reach the artifact-ingestion
contract. Re-exports, with object identity preserved, the five contract symbols
consumed by ``layer3_workbench``:

* ``validate_target_artifact_payload``            -- target-payload validator
* ``APS_ARTIFACT_INGESTION_SCHEMA_VERSION``       -- accepted schema version (== 1)
* ``APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID``     -- "aps.artifact_ingestion_target.v1"
* ``APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID``        -- "aps.artifact_ingestion_run.v1"
* ``APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE`` -- refusal failure code

``ArtifactIngestionContract`` (typing.Protocol) documents that surface; the
one-key ``ARTIFACT_INGESTION_PROVIDERS`` registry names the sole current
provider ("nrc_aps"). Both are declarations only.

Behavior neutrality (Tier-1)
----------------------------
No behavior lives here. Every re-exported name binds the *same object* defined
in ``app.services.nrc_aps_artifact_ingestion``; this module adds a naming seam,
not logic. Flipping a consumer from the concrete module to this facade is a
provably behavior-neutral change (see the identity/parity tests).

Phase-2 provenance
------------------
Implements the "Neutral NRC APS facade -- Tier-1 (code, behavior-neutral)" row
of the Phase-2 plan in
``next_milestone_plans/Layer3_planning_docs/1366-source-artifact-admission-map.md``.
The registry is the extension point for future ingestion providers: new
providers register here without any consumer edit.
"""
from __future__ import annotations

from typing import Any, Protocol

from app.services import nrc_aps_artifact_ingestion

# Identity-preserving re-export of the consumed contract surface.
validate_target_artifact_payload = nrc_aps_artifact_ingestion.validate_target_artifact_payload
APS_ARTIFACT_INGESTION_SCHEMA_VERSION = nrc_aps_artifact_ingestion.APS_ARTIFACT_INGESTION_SCHEMA_VERSION
APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID = nrc_aps_artifact_ingestion.APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID
APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID = nrc_aps_artifact_ingestion.APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID
APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE = nrc_aps_artifact_ingestion.APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE


class ArtifactIngestionContract(Protocol):
    """Structural contract for an artifact-ingestion provider (declaration only)."""

    APS_ARTIFACT_INGESTION_SCHEMA_VERSION: int
    APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID: str
    APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID: str
    APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE: str

    def validate_target_artifact_payload(self, payload: dict[str, Any]) -> list[str]: ...


# Sole current provider; new providers register here without consumer edits.
ARTIFACT_INGESTION_PROVIDERS: dict[str, ArtifactIngestionContract] = {
    "nrc_aps": nrc_aps_artifact_ingestion,
}

__all__ = [
    "validate_target_artifact_payload",
    "APS_ARTIFACT_INGESTION_SCHEMA_VERSION",
    "APS_ARTIFACT_INGESTION_TARGET_SCHEMA_ID",
    "APS_ARTIFACT_INGESTION_RUN_SCHEMA_ID",
    "APS_FAILURE_ARTIFACT_UNSUPPORTED_MEDIA_TYPE",
    "ArtifactIngestionContract",
    "ARTIFACT_INGESTION_PROVIDERS",
]
