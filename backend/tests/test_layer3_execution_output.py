from __future__ import annotations

# ruff: noqa: E402

import hashlib
import io
import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.db.session import Base
from app.models.models import AnalysisArtifact, L3PassRun
from app.services import layer3_execution_output as execution_output
from app.services import layer3_pass_entry
from app.services import layer3_workbench
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_STATUS_FAILED,
    PASS_TYPE_SINGLE_ITEM,
)


@pytest.fixture
def managed_artifact_root(tmp_path, monkeypatch) -> Path:
    storage_dir = tmp_path / "storage"
    artifact_root = storage_dir / "artifacts"
    (artifact_root / "layer3").mkdir(parents=True)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    return artifact_root


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


def _artifact(
    *,
    artifact_id: str,
    artifact_type: str,
    storage_ref: Path,
) -> AnalysisArtifact:
    return AnalysisArtifact(
        artifact_id=artifact_id,
        analysis_run_id="analysis-run-output",
        artifact_type=artifact_type,
        title=artifact_id,
        storage_ref=str(storage_ref),
        metadata_json={},
    )


def _origin_integrity() -> dict:
    return {
        "schema_id": "layer3.connector_origin_integrity.v1",
        "connector_key": "sciencebase_mcs",
        "connector_run_target_id": "target-output",
        "connector_origin_receipt_hash": "a" * 64,
        "proof_class": "offline_fixture",
    }


def test_output_integrity_receipts_are_sorted_and_stable(
    managed_artifact_root: Path,
) -> None:
    table_path = managed_artifact_root / "table.bin"
    chart_path = managed_artifact_root / "chart.bin"
    manifest_path = managed_artifact_root / "layer3" / "output.json"
    table_path.write_bytes(b"table")
    chart_path.write_bytes(b"chart-bytes")
    manifest_bytes = b'{\n  "artifact_refs_json": []\n}\n'
    manifest_path.write_bytes(manifest_bytes)
    table = _artifact(
        artifact_id="artifact-z",
        artifact_type="table",
        storage_ref=table_path,
    )
    chart = _artifact(
        artifact_id="artifact-a",
        artifact_type="chart",
        storage_ref=chart_path,
    )

    projection = execution_output.compute_output_integrity(
        [table, chart],
        output_manifest_ref=str(manifest_path),
    )
    replay = execution_output.compute_output_integrity(
        [chart, table],
        output_manifest_ref=str(manifest_path),
    )

    expected_receipts = [
        {
            "artifact_id": "artifact-a",
            "artifact_type": "chart",
            "artifact_sha256": hashlib.sha256(b"chart-bytes").hexdigest(),
            "artifact_size_bytes": len(b"chart-bytes"),
        },
        {
            "artifact_id": "artifact-z",
            "artifact_type": "table",
            "artifact_sha256": hashlib.sha256(b"table").hexdigest(),
            "artifact_size_bytes": len(b"table"),
        },
    ]
    assert projection == replay
    assert projection["artifact_receipts"] == expected_receipts
    assert projection["artifact_set_hash"] == hashlib.sha256(
        json.dumps(
            expected_receipts,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert projection["output_manifest_sha256"] == hashlib.sha256(
        manifest_bytes
    ).hexdigest()


def test_connector_output_integrity_has_exact_schema_and_origin_binding(
    managed_artifact_root: Path,
) -> None:
    artifact_path = managed_artifact_root / "connector-output.bin"
    manifest_path = managed_artifact_root / "layer3" / "connector-output.json"
    artifact_path.write_bytes(b"connector-output")
    manifest_path.write_bytes(b"{}")
    artifact = _artifact(
        artifact_id="artifact-connector-output",
        artifact_type="descriptive_summary_result",
        storage_ref=artifact_path,
    )

    integrity = execution_output.build_connector_output_integrity(
        [artifact],
        output_manifest_ref=str(manifest_path),
        connector_origin_integrity=_origin_integrity(),
    )

    assert list(integrity) == [
        "schema_id",
        "connector_key",
        "connector_run_target_id",
        "connector_origin_receipt_hash",
        "proof_class",
        "artifact_receipts",
        "artifact_set_hash",
        "output_manifest_sha256",
    ]
    assert integrity["schema_id"] == "layer3.connector_output_integrity.v1"
    assert integrity["connector_key"] == "sciencebase_mcs"
    assert integrity["artifact_receipts"][0]["artifact_id"] == artifact.artifact_id


def test_pass_output_integrity_uses_complete_durable_artifact_set(
    managed_artifact_root: Path,
    tmp_path: Path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'output-authority.db'}",
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    first_path = managed_artifact_root / "complete-first.bin"
    second_path = managed_artifact_root / "complete-second.bin"
    manifest_path = managed_artifact_root / "layer3" / "complete.json"
    first_path.write_bytes(b"first")
    second_path.write_bytes(b"second")
    manifest_path.write_text(
        json.dumps(
            {
                "analysis_run_id": "analysis-run-output",
                "artifact_refs_json": [str(first_path), str(second_path)],
                "artifact_types_json": [
                    "descriptive_summary_result",
                    "supporting_table",
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    first = _artifact(
        artifact_id="artifact-complete-first",
        artifact_type="descriptive_summary_result",
        storage_ref=first_path,
    )
    second = _artifact(
        artifact_id="artifact-complete-second",
        artifact_type="supporting_table",
        storage_ref=second_path,
    )
    origin_integrity = _origin_integrity()
    stored_integrity = execution_output.build_connector_output_integrity(
        [first, second],
        output_manifest_ref=str(manifest_path),
        connector_origin_integrity=origin_integrity,
    )
    receipts = {
        receipt["artifact_id"]: receipt
        for receipt in stored_integrity["artifact_receipts"]
    }
    for artifact in (first, second):
        receipt = receipts[artifact.artifact_id]
        artifact.metadata_json = {
            "artifact_sha256": receipt["artifact_sha256"],
            "artifact_size_bytes": receipt["artifact_size_bytes"],
            "connector_origin_receipt_hash": origin_integrity[
                "connector_origin_receipt_hash"
            ],
            "proof_class": origin_integrity["proof_class"],
        }
    pass_run = _pass_run(str(manifest_path))
    pass_run.summary_json = {
        "analysis_run_id": "analysis-run-output",
        "connector_origin_integrity_v1": origin_integrity,
        "connector_output_integrity_v1": stored_integrity,
    }

    try:
        with SessionLocal() as db:
            db.add_all([pass_run, first, second])
            db.commit()
            durable = execution_output.assert_pass_output_integrity(
                db,
                pass_run_id=pass_run.pass_run_id,
            )
            assert [
                receipt["artifact_id"]
                for receipt in durable["artifact_receipts"]
            ] == [
                "artifact-complete-first",
                "artifact-complete-second",
            ]

            third_path = managed_artifact_root / "complete-third.bin"
            third_path.write_bytes(b"third")
            db.add(
                _artifact(
                    artifact_id="artifact-complete-third",
                    artifact_type="supporting_table",
                    storage_ref=third_path,
                )
            )
            db.commit()

            with pytest.raises(
                execution_output.Layer3ExecutionOutputIntegrityError
            ) as excinfo:
                execution_output.assert_pass_output_integrity(
                    db,
                    pass_run_id=pass_run.pass_run_id,
                )
            assert excinfo.value.code == "layer3_output_integrity_mismatch"
    finally:
        engine.dispose()


def test_pass_output_integrity_rejects_flushed_uncommitted_authority(
    managed_artifact_root: Path,
    tmp_path: Path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'output-uncommitted.db'}",
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    artifact_path = managed_artifact_root / "uncommitted.bin"
    manifest_path = managed_artifact_root / "layer3" / "uncommitted.json"
    artifact_path.write_bytes(b"committed")
    manifest_path.write_text(
        json.dumps(
            {
                "analysis_run_id": "analysis-run-output",
                "artifact_refs_json": [str(artifact_path)],
                "artifact_types_json": ["descriptive_summary_result"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    artifact = _artifact(
        artifact_id="artifact-uncommitted",
        artifact_type="descriptive_summary_result",
        storage_ref=artifact_path,
    )
    origin_integrity = _origin_integrity()
    committed_integrity = execution_output.build_connector_output_integrity(
        [artifact],
        output_manifest_ref=str(manifest_path),
        connector_origin_integrity=origin_integrity,
    )
    committed_receipt = committed_integrity["artifact_receipts"][0]
    artifact.metadata_json = {
        "artifact_sha256": committed_receipt["artifact_sha256"],
        "artifact_size_bytes": committed_receipt["artifact_size_bytes"],
        "connector_origin_receipt_hash": origin_integrity[
            "connector_origin_receipt_hash"
        ],
        "proof_class": origin_integrity["proof_class"],
    }
    pass_run = _pass_run(str(manifest_path))
    pass_run.summary_json = {
        "analysis_run_id": "analysis-run-output",
        "connector_origin_integrity_v1": origin_integrity,
        "connector_output_integrity_v1": committed_integrity,
    }

    try:
        with SessionLocal() as db:
            db.add_all([pass_run, artifact])
            db.commit()

            artifact_path.write_bytes(b"flushed-uncommitted")
            stored_artifact = db.get(
                AnalysisArtifact,
                "artifact-uncommitted",
            )
            stored_pass = db.get(L3PassRun, pass_run.pass_run_id)
            assert stored_artifact is not None
            assert stored_pass is not None
            forged_integrity = execution_output.build_connector_output_integrity(
                [stored_artifact],
                output_manifest_ref=str(manifest_path),
                connector_origin_integrity=origin_integrity,
            )
            forged_receipt = forged_integrity["artifact_receipts"][0]
            stored_artifact.metadata_json = {
                "artifact_sha256": forged_receipt["artifact_sha256"],
                "artifact_size_bytes": forged_receipt[
                    "artifact_size_bytes"
                ],
                "connector_origin_receipt_hash": origin_integrity[
                    "connector_origin_receipt_hash"
                ],
                "proof_class": origin_integrity["proof_class"],
            }
            stored_pass.summary_json = {
                **stored_pass.summary_json,
                "connector_output_integrity_v1": forged_integrity,
            }
            db.flush()

            with pytest.raises(
                execution_output.Layer3ExecutionOutputIntegrityError
            ) as excinfo:
                execution_output.assert_pass_output_integrity(
                    db,
                    pass_run_id=pass_run.pass_run_id,
                )
            assert excinfo.value.code == "layer3_output_uncommitted_authority"
    finally:
        engine.dispose()


def test_selected_execution_failure_preserves_outer_transaction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'execution-savepoint.db'}",
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    pass_run = _pass_run(None)
    pass_run.status = layer3_pass_entry.PASS_STATUS_SELECTED_NOT_STARTED
    pass_run.summary_json = {
        "planned_pass": {
            "pass_type": PASS_TYPE_SINGLE_ITEM,
            "dataset_version_id": "dataset-version-savepoint",
            "selected_method_name": "descriptive_summary",
        }
    }

    def fail_analysis(db, **kwargs):
        assert kwargs["commit"] is False
        db.add(
            AnalysisArtifact(
                artifact_id="artifact-savepoint",
                analysis_run_id="analysis-run-savepoint",
                artifact_type="descriptive_summary_result",
                title="savepoint",
                storage_ref="payload://savepoint",
                metadata_json={},
            )
        )
        db.flush()
        raise RuntimeError("analysis failed")

    monkeypatch.setattr(
        layer3_pass_entry,
        "assert_pass_downstream_connector_origin",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        layer3_pass_entry,
        "run_analysis",
        fail_analysis,
    )

    try:
        with SessionLocal() as db:
            db.add(pass_run)
            db.commit()
            db.begin()
            stored_pass = db.get(L3PassRun, pass_run.pass_run_id)
            assert stored_pass is not None
            outer_transaction = db.get_transaction()
            assert outer_transaction is not None

            result = layer3_pass_entry.execute_selected_pass_run(
                db,
                pass_run=stored_pass,
                planned_pass=stored_pass.summary_json["planned_pass"],
                client_request_id="request-savepoint",
            )

            assert db.get_transaction() is outer_transaction
            assert result.status == PASS_STATUS_FAILED
            assert (
                db.query(AnalysisArtifact)
                .filter(
                    AnalysisArtifact.artifact_id == "artifact-savepoint"
                )
                .count()
                == 0
            )
    finally:
        engine.dispose()


def test_output_manifest_publication_does_not_follow_hardlink(
    managed_artifact_root: Path,
) -> None:
    victim = managed_artifact_root / "victim.json"
    victim.write_bytes(b"preserve-me")
    target = (
        managed_artifact_root
        / "layer3"
        / "l3_pass_run_pass-run-hardlink.json"
    )
    os.link(victim, target)

    with pytest.raises(layer3_pass_entry.Layer3PassEntryError):
        layer3_pass_entry._persist_output_manifest(  # type: ignore[attr-defined]
            pass_run_id="pass-run-hardlink",
            payload={"analysis_run_id": "analysis-run-hardlink"},
        )

    assert victim.read_bytes() == b"preserve-me"


def test_output_manifest_publication_ignores_timestamp_only_churn(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    original_managed_file = execution_output._managed_regular_file
    churned = False

    def churn_before_publication_stat(root: Path, path: Path):
        nonlocal churned
        if not churned and path.name == "l3_pass_run_pass-run-timestamp.json":
            info = path.stat()
            os.utime(
                path,
                ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000),
            )
            assert path.stat().st_mtime_ns != info.st_mtime_ns
            churned = True
        return original_managed_file(root, path)

    monkeypatch.setattr(
        execution_output,
        "_managed_regular_file",
        churn_before_publication_stat,
    )

    output_ref = execution_output.persist_output_manifest(
        pass_run_id="pass-run-timestamp",
        payload={"analysis_run_id": "analysis-run-timestamp"},
    )

    assert churned is True
    assert Path(output_ref).is_file()


def test_bounded_hash_stream_rejects_growth_after_one_overread() -> None:
    stream = io.BytesIO(b"123456789")

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output._bounded_hash_stream(  # type: ignore[attr-defined]
            stream,
            max_bytes=4,
            capture_bytes=False,
        )

    assert excinfo.value.code == "layer3_output_file_invalid"
    assert stream.tell() == 5


def test_artifact_set_hash_canonicalizes_and_validates_receipts() -> None:
    receipts = [
        {
            "artifact_id": "artifact-z",
            "artifact_type": "table",
            "artifact_sha256": "b" * 64,
            "artifact_size_bytes": 2,
        },
        {
            "artifact_id": "artifact-a",
            "artifact_type": "chart",
            "artifact_sha256": "a" * 64,
            "artifact_size_bytes": 1,
        },
    ]

    assert execution_output.artifact_set_hash(
        receipts
    ) == execution_output.artifact_set_hash(list(reversed(receipts)))
    for invalid in (
        [{**receipts[0], "unexpected": True}],
        [receipts[0], {**receipts[1], "artifact_id": "artifact-z"}],
    ):
        with pytest.raises(
            execution_output.Layer3ExecutionOutputIntegrityError
        ) as excinfo:
            execution_output.artifact_set_hash(invalid)
        assert excinfo.value.code == "layer3_output_artifact_receipt_invalid"


def test_artifact_receipts_resolve_logical_storage_ref(
    managed_artifact_root: Path,
) -> None:
    artifact_path = managed_artifact_root / "logical.bin"
    artifact_path.write_bytes(b"logical-bytes")
    artifact = _artifact(
        artifact_id="artifact-logical",
        artifact_type="table",
        storage_ref=Path("/storage/artifacts/logical.bin"),
    )

    assert execution_output.artifact_receipts([artifact]) == [
        {
            "artifact_id": "artifact-logical",
            "artifact_type": "table",
            "artifact_sha256": hashlib.sha256(b"logical-bytes").hexdigest(),
            "artifact_size_bytes": len(b"logical-bytes"),
        }
    ]


def test_artifact_receipts_accept_contained_absolute_ref(
    managed_artifact_root: Path,
) -> None:
    artifact_path = managed_artifact_root / "absolute.bin"
    artifact_path.write_bytes(b"absolute")
    artifact = _artifact(
        artifact_id="artifact-absolute",
        artifact_type="table",
        storage_ref=artifact_path,
    )

    assert execution_output.artifact_receipts([artifact]) == [
        {
            "artifact_id": "artifact-absolute",
            "artifact_type": "table",
            "artifact_sha256": hashlib.sha256(b"absolute").hexdigest(),
            "artifact_size_bytes": len(b"absolute"),
        }
    ]


def test_artifact_cardinality_fails_before_handle_reads(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    artifact_path = managed_artifact_root / "cardinality.bin"
    artifact_path.write_bytes(b"x")
    artifacts = [
        _artifact(
            artifact_id=f"artifact-{index}",
            artifact_type="table",
            storage_ref=artifact_path,
        )
        for index in range(2)
    ]
    monkeypatch.setattr(
        execution_output,
        "MAX_OUTPUT_ARTIFACTS",
        1,
        raising=False,
    )

    def forbidden_read(*args, **kwargs):
        del args, kwargs
        raise AssertionError("cardinality failure reached handle reads")

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        forbidden_read,
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.artifact_receipts(artifacts)

    assert excinfo.value.code == "layer3_output_work_bound_exceeded"


def test_artifact_aggregate_bytes_fail_before_handle_reads(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    artifacts = []
    for index in range(2):
        path = managed_artifact_root / f"aggregate-{index}.bin"
        path.write_bytes(b"abc")
        artifacts.append(
            _artifact(
                artifact_id=f"aggregate-{index}",
                artifact_type="table",
                storage_ref=path,
            )
        )
    monkeypatch.setattr(
        execution_output,
        "MAX_OUTPUT_AGGREGATE_BYTES",
        5,
        raising=False,
    )

    def forbidden_read(*args, **kwargs):
        del args, kwargs
        raise AssertionError("aggregate failure reached handle reads")

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        forbidden_read,
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.artifact_receipts(artifacts)

    assert excinfo.value.code == "layer3_output_work_bound_exceeded"


def test_output_integrity_combined_bytes_fail_before_handle_reads(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    artifact_path = managed_artifact_root / "combined.bin"
    manifest_path = managed_artifact_root / "layer3" / "combined.json"
    artifact_path.write_bytes(b"abcd")
    manifest_path.write_bytes(b"{}")
    artifact = _artifact(
        artifact_id="combined",
        artifact_type="table",
        storage_ref=artifact_path,
    )
    monkeypatch.setattr(
        execution_output,
        "MAX_OUTPUT_AGGREGATE_BYTES",
        5,
        raising=False,
    )

    def forbidden_read(*args, **kwargs):
        del args, kwargs
        raise AssertionError("combined failure reached handle reads")

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        forbidden_read,
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.compute_output_integrity(
            [artifact],
            output_manifest_ref=str(manifest_path),
        )

    assert excinfo.value.code == "layer3_output_work_bound_exceeded"


@pytest.mark.parametrize(
    "configured_root",
    (
        "relative-storage",
        r"\\server\share\storage",
        r"\\?\C:\task7-storage",
        r"C:\tmp\NUL",
    ),
)
def test_artifact_receipts_reject_invalid_configured_root_before_io(
    monkeypatch,
    configured_root: str,
) -> None:
    monkeypatch.setattr(settings, "storage_dir", configured_root)

    def forbidden_read(*args, **kwargs):
        del args, kwargs
        raise AssertionError("invalid configured root reached handle reads")

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        forbidden_read,
    )
    artifact = _artifact(
        artifact_id="relative-root",
        artifact_type="table",
        storage_ref=Path("artifact.bin"),
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.artifact_receipts([artifact])

    assert excinfo.value.code == "layer3_output_binding_invalid"


def test_artifact_refs_reject_unmanaged_or_unsafe_paths_before_io(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    attempted_io = False

    def forbidden_io(*args, **kwargs):
        nonlocal attempted_io
        attempted_io = True
        raise AssertionError(
            f"unsafe path reached file I/O: {args[1] if len(args) > 1 else kwargs}"
        )

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        forbidden_io,
    )
    invalid_refs = (
        managed_artifact_root.parent.parent / "outside.bin",
        Path("../outside.bin"),
        Path(r"\\server\share\secret.bin"),
        Path(r"\\?\C:\secret.bin"),
        managed_artifact_root / "artifact.bin:secret",
    )

    for index, storage_ref in enumerate(invalid_refs):
        with pytest.raises(
            execution_output.Layer3ExecutionOutputIntegrityError
        ) as excinfo:
            execution_output.artifact_receipts(
                [
                    _artifact(
                        artifact_id=f"unsafe-{index}",
                        artifact_type="table",
                        storage_ref=storage_ref,
                    )
                ]
            )
        assert excinfo.value.code == "layer3_output_binding_invalid"
    assert attempted_io is False


def test_artifact_receipts_reject_parent_reparse_component(
    managed_artifact_root: Path,
) -> None:
    real_dir = managed_artifact_root / "real"
    alias_dir = managed_artifact_root / "alias"
    real_dir.mkdir()
    artifact_path = real_dir / "artifact.bin"
    artifact_path.write_bytes(b"reparse")
    try:
        alias_dir.symlink_to(real_dir, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.artifact_receipts(
            [
                _artifact(
                    artifact_id="artifact-reparse",
                    artifact_type="table",
                    storage_ref=alias_dir / artifact_path.name,
                )
            ]
        )

    assert excinfo.value.code == "layer3_output_binding_invalid"


def test_output_integrity_recomputes_artifact_bytes(
    managed_artifact_root: Path,
) -> None:
    artifact_path = managed_artifact_root / "artifact.bin"
    manifest_path = managed_artifact_root / "layer3" / "output.json"
    artifact_path.write_bytes(b"authoritative")
    manifest_path.write_bytes(b"{}")
    artifact = _artifact(
        artifact_id="artifact-one",
        artifact_type="table",
        storage_ref=artifact_path,
    )
    expected = execution_output.compute_output_integrity(
        [artifact],
        output_manifest_ref=str(manifest_path),
    )
    artifact_path.write_bytes(b"Authoritative")

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.assert_output_integrity(
            [artifact],
            output_manifest_ref=str(manifest_path),
            expected_integrity=expected,
        )

    assert excinfo.value.code == "layer3_output_integrity_mismatch"


@pytest.mark.parametrize("kind", ["missing", "directory"])
def test_output_manifest_hash_fails_closed_for_invalid_paths(
    managed_artifact_root: Path,
    kind: str,
) -> None:
    manifest_path = managed_artifact_root / "layer3" / "output.json"
    if kind == "directory":
        manifest_path.mkdir()

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.output_manifest_sha256(str(manifest_path))

    assert excinfo.value.code == "layer3_output_file_invalid"


def test_output_manifest_hash_rejects_a_changing_file(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    manifest_path = managed_artifact_root / "layer3" / "output.json"
    manifest_path.write_bytes(b"{}")

    def changing_snapshot(*args, **kwargs):
        del args, kwargs
        raise execution_output.Layer3ExecutionOutputIntegrityError(
            "layer3_output_file_changed",
            "changed",
        )

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        changing_snapshot,
        raising=False,
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output.output_manifest_sha256(str(manifest_path))

    assert excinfo.value.code == "layer3_output_file_changed"


def test_stable_managed_file_ignores_timestamp_only_churn(
    managed_artifact_root: Path,
) -> None:
    root = managed_artifact_root / "layer3"
    manifest_path = root / "timestamp-churn.json"
    payload = b'{"stable":true}'
    manifest_path.write_bytes(payload)
    initial = execution_output._managed_regular_file(root, manifest_path)

    os.utime(
        manifest_path,
        ns=(initial.st_atime_ns, initial.st_mtime_ns + 1_000_000_000),
    )
    assert manifest_path.stat().st_mtime_ns != initial.st_mtime_ns

    assert execution_output._stable_managed_file(
        root,
        manifest_path,
        initial=initial,
        read_bytes=True,
    ) == (len(payload), hashlib.sha256(payload).hexdigest(), payload)


def test_stable_managed_file_rejects_same_size_content_change_between_hashes(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    root = managed_artifact_root / "layer3"
    manifest_path = root / "content-churn.json"
    manifest_path.write_bytes(b"before")
    original_hash_stream = execution_output._bounded_hash_stream
    hash_count = 0

    def mutate_after_first_hash(*args, **kwargs):
        nonlocal hash_count
        result = original_hash_stream(*args, **kwargs)
        hash_count += 1
        if hash_count == 1:
            manifest_path.write_bytes(b"after!")
        return result

    monkeypatch.setattr(
        execution_output,
        "_bounded_hash_stream",
        mutate_after_first_hash,
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output._stable_managed_file(root, manifest_path)

    assert excinfo.value.code == "layer3_output_file_changed"
    assert hash_count == 2


def test_stable_managed_file_rejects_same_size_content_change_after_hashes(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    root = managed_artifact_root / "layer3"
    manifest_path = root / "late-content-churn.json"
    manifest_path.write_bytes(b"before")
    original_hash_stream = execution_output._bounded_hash_stream
    hash_count = 0

    def mutate_after_second_hash(*args, **kwargs):
        nonlocal hash_count
        result = original_hash_stream(*args, **kwargs)
        hash_count += 1
        if hash_count == 2:
            manifest_path.write_bytes(b"after!")
        return result

    monkeypatch.setattr(
        execution_output,
        "_bounded_hash_stream",
        mutate_after_second_hash,
    )

    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as excinfo:
        execution_output._stable_managed_file(root, manifest_path)

    assert excinfo.value.code == "layer3_output_file_changed"
    assert hash_count == 3


def test_output_integrity_rejects_unreadable_and_over_cap_files(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    artifact_path = managed_artifact_root / "bounded.bin"
    artifact_path.write_bytes(b"12345")
    artifact = _artifact(
        artifact_id="artifact-bounded",
        artifact_type="table",
        storage_ref=artifact_path,
    )
    monkeypatch.setattr(
        execution_output,
        "MAX_OUTPUT_FILE_BYTES",
        4,
        raising=False,
    )
    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as over_cap:
        execution_output.artifact_receipts([artifact])
    assert over_cap.value.code == "layer3_output_file_invalid"

    def unreadable_snapshot(*args, **kwargs):
        del args, kwargs
        raise execution_output.Layer3ExecutionOutputIntegrityError(
            "layer3_output_file_unreadable",
            "io",
        )

    monkeypatch.setattr(
        execution_output,
        "MAX_OUTPUT_FILE_BYTES",
        64,
        raising=False,
    )
    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        unreadable_snapshot,
        raising=False,
    )
    with pytest.raises(
        execution_output.Layer3ExecutionOutputIntegrityError
    ) as unreadable:
        execution_output.artifact_receipts([artifact])
    assert unreadable.value.code == "layer3_output_file_unreadable"


def test_output_manifest_requires_canonical_layer3_managed_path(
    managed_artifact_root: Path,
) -> None:
    canonical = managed_artifact_root / "layer3" / "manifest.json"
    canonical.write_bytes(b"{}")
    assert execution_output.output_manifest_sha256(
        str(canonical)
    ) == hashlib.sha256(b"{}").hexdigest()

    for invalid in (
        managed_artifact_root / "not-layer3.json",
        managed_artifact_root.parent / "outside.json",
        Path("../manifest.json"),
    ):
        with pytest.raises(
            execution_output.Layer3ExecutionOutputIntegrityError
        ) as excinfo:
            execution_output.output_manifest_sha256(str(invalid))
        assert excinfo.value.code == "layer3_output_binding_invalid"


def test_assert_output_integrity_requires_exact_stored_shape(
    managed_artifact_root: Path,
) -> None:
    artifact_path = managed_artifact_root / "shape.bin"
    manifest_path = managed_artifact_root / "layer3" / "shape.json"
    artifact_path.write_bytes(b"shape")
    manifest_path.write_bytes(b"{}")
    artifact = _artifact(
        artifact_id="artifact-shape",
        artifact_type="table",
        storage_ref=artifact_path,
    )
    expected = execution_output.compute_output_integrity(
        [artifact],
        output_manifest_ref=str(manifest_path),
    )

    for malformed in (
        {**expected, "unexpected": True},
        {
            key: value
            for key, value in expected.items()
            if key != "artifact_set_hash"
        },
    ):
        with pytest.raises(
            execution_output.Layer3ExecutionOutputIntegrityError
        ) as excinfo:
            execution_output.assert_output_integrity(
                [artifact],
                output_manifest_ref=str(manifest_path),
                expected_integrity=malformed,
            )
        assert excinfo.value.code == "layer3_output_integrity_mismatch"


def test_output_metadata_summary_preserves_missing_and_invalid_error_semantics(
    managed_artifact_root: Path,
) -> None:
    output_root = managed_artifact_root / "layer3"
    assert execution_output.output_metadata_summary(_pass_run(None)) == (
        None,
        "output_payload_ref_missing",
    )
    assert execution_output.output_metadata_summary(_pass_run(str(output_root / "missing.json"))) == (
        None,
        "output_metadata_file_missing",
    )

    unreadable = output_root / "unreadable.json"
    unreadable.write_text("{not-json", encoding="utf-8")
    assert execution_output.output_metadata_summary(_pass_run(str(unreadable))) == (
        None,
        "output_metadata_unreadable",
    )

    malformed = output_root / "malformed.json"
    malformed.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert execution_output.output_metadata_summary(_pass_run(str(malformed))) == (
        None,
        "output_metadata_malformed",
    )


def test_output_metadata_summary_rejects_unmanaged_path_without_reading(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    outside = managed_artifact_root.parent / "outside.json"
    outside.write_text('{"artifact_refs_json":[]}', encoding="utf-8")

    def forbidden_read(*args, **kwargs):
        del args, kwargs
        raise AssertionError("unmanaged summary reached handle reads")

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        forbidden_read,
    )

    assert execution_output.output_metadata_summary(
        _pass_run(str(outside))
    ) == (None, "output_metadata_unreadable")


def test_output_metadata_summary_rejects_reparse_path(
    managed_artifact_root: Path,
) -> None:
    output_root = managed_artifact_root / "layer3"
    real = output_root / "real.json"
    alias = output_root / "alias.json"
    real.write_text('{"artifact_refs_json":[]}', encoding="utf-8")
    try:
        alias.symlink_to(real)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    assert execution_output.output_metadata_summary(
        _pass_run(str(alias))
    ) == (None, "output_metadata_unreadable")


def test_output_metadata_summary_rejects_oversized_file(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    output = managed_artifact_root / "layer3" / "oversized.json"
    output.write_text('{"artifact_refs_json":[]}', encoding="utf-8")
    monkeypatch.setattr(
        execution_output,
        "MAX_OUTPUT_FILE_BYTES",
        4,
        raising=False,
    )

    assert execution_output.output_metadata_summary(
        _pass_run(str(output))
    ) == (None, "output_metadata_unreadable")


def test_output_metadata_summary_rejects_changing_file(
    managed_artifact_root: Path,
    monkeypatch,
) -> None:
    output = managed_artifact_root / "layer3" / "changing.json"
    payload = b'{"artifact_refs_json":[]}'
    output.write_bytes(payload)

    def changing_snapshot(*args, **kwargs):
        del args, kwargs
        raise execution_output.Layer3ExecutionOutputIntegrityError(
            "layer3_output_file_changed",
            "changed",
        )

    monkeypatch.setattr(
        execution_output,
        "_stable_managed_file",
        changing_snapshot,
    )

    assert execution_output.output_metadata_summary(
        _pass_run(str(output))
    ) == (None, "output_metadata_unreadable")


def test_output_metadata_summary_preserves_workbench_projection(
    managed_artifact_root: Path,
) -> None:
    output = managed_artifact_root / "layer3" / "output.json"
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
