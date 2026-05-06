from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3PassRun
from app.services import layer3_execution_output as execution_output
from app.services import layer3_workbench
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_TYPE_SINGLE_ITEM,
)


def _pass_run(output_payload_ref: str | None) -> L3PassRun:
    return L3PassRun(
        pass_run_id="pass-run-output",
        session_id="session-output",
        analysis_plan_id="plan-output",
        analysis_set_id="set-output",
        pass_type=PASS_TYPE_SINGLE_ITEM,
        engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
        status=PASS_STATUS_COMPLETED,
        input_payload_ref="payload://input",
        output_payload_ref=output_payload_ref,
        summary_json={},
    )


def test_output_metadata_summary_preserves_missing_and_invalid_error_semantics(tmp_path) -> None:
    assert execution_output.output_metadata_summary(_pass_run(None)) == (
        None,
        "output_payload_ref_missing",
    )
    assert execution_output.output_metadata_summary(_pass_run(str(tmp_path / "missing.json"))) == (
        None,
        "output_metadata_file_missing",
    )

    unreadable = tmp_path / "unreadable.json"
    unreadable.write_text("{not-json", encoding="utf-8")
    assert execution_output.output_metadata_summary(_pass_run(str(unreadable))) == (
        None,
        "output_metadata_unreadable",
    )

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert execution_output.output_metadata_summary(_pass_run(str(malformed))) == (
        None,
        "output_metadata_malformed",
    )


def test_output_metadata_summary_preserves_workbench_projection(tmp_path) -> None:
    output = tmp_path / "output.json"
    output.write_text(
        json.dumps(
            {
                "analysis_run_id": "analysis-run-output",
                "analysis_set_id": "set-output",
                "dataset_version_id": "dataset-version-output",
                "selected_method_name": "descriptive_summary",
                "artifact_refs_json": ["artifact://one", "artifact://two"],
                "artifact_types_json": ["table", "chart"],
                "source_gate": "source-gate-output",
                "pass_scope": "single_item",
                "source_dataset_version_ids_json": ["dataset-version-output"],
                "cohort_shape": "wide_table",
                "requested_method_name": "descriptive_summary",
                "requested_method_source": "operator",
                "engine_family": ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
                "pass_type": PASS_TYPE_SINGLE_ITEM,
                "source_shape": "dataset_version",
                "material_snapshot_id": "snapshot-output",
                "analysis_unit_id": "unit-output",
                "document_identity": {"content_id": "content-output"},
                "chunk_summary": {
                    "chunk_ids": ["chunk-a", "chunk-b"],
                    "chunk_hashes": ["hash-a", "hash-b"],
                },
            }
        ),
        encoding="utf-8",
    )
    pass_run = _pass_run(str(output))

    summary, error = execution_output.output_metadata_summary(pass_run)

    assert error is None
    assert summary == layer3_workbench._output_metadata_summary(pass_run)[0]
    assert summary["present"] is True
    assert summary["readable"] is True
    assert summary["artifact_count"] == 2
    assert summary["artifact_refs"] == ["artifact://one", "artifact://two"]
    assert summary["source_dataset_version_ids"] == ["dataset-version-output"]
    assert summary["content_id"] == "content-output"
    assert summary["chunk_ids"] == ["chunk-a", "chunk-b"]
    assert summary["chunk_hashes"] == ["hash-a", "hash-b"]
