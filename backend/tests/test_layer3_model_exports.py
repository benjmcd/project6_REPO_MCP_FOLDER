from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import app.models as exported_models
import app.models.models as canonical_models


L3_MODEL_NAMES = (
    "L3AnalysisGroup",
    "L3AnalysisPlan",
    "L3AnalysisSet",
    "L3AnalysisUnit",
    "L3Descriptor",
    "L3MaterialSnapshot",
    "L3OutputPackage",
    "L3PassRun",
    "L3ReconciliationRecord",
    "L3RetrievalEvent",
    "L3SelectionManifest",
    "L3Session",
    "L3SignedReferenceAuditEvent",
    "L3SignedReferenceReceipt",
    "L3SignedReferenceRevocation",
    "L3SignedReferenceToken",
    "L3TypingRecord",
)


def test_layer3_models_are_reexported_from_app_models() -> None:
    for model_name in L3_MODEL_NAMES:
        assert getattr(exported_models, model_name) is getattr(canonical_models, model_name)
