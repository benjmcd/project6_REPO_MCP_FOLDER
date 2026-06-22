from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPLAY_PATH = ROOT / "diagnostics" / "assessment" / "sec-live-replay.py"


def _replay_module():
    spec = importlib.util.spec_from_file_location("sec_live_replay", REPLAY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _replay_files(runtime_root: Path) -> tuple[list[Path], list[Path]]:
    receipt_files = sorted(runtime_root.rglob("receipts/*.json"))
    artifact_files = sorted(runtime_root.rglob("artifacts/*.txt"))
    return receipt_files, artifact_files


def test_sec_live_replay_runs_full_mocked_acquire_to_redacted_provenance(tmp_path: Path) -> None:
    module = _replay_module()
    runtime_root = tmp_path / "runtime"

    report = module.build_report(source_root=ROOT, runtime_root=runtime_root)
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "sec_live_source_artifact_offline_replay_proven"
    assert report["criteria"]
    assert all(item["state"] == "passed" for item in report["criteria"])
    assert report["offline_replay"]["fixture_hash"] == report["server_readback"]["content_sha256"]
    assert report["offline_replay"]["fixture_length"] == report["server_readback"]["content_length"]
    assert report["offline_replay"]["transport_call_count"] == 1
    assert report["offline_replay"]["idempotent_replay"] is True
    assert report["offline_replay"]["status_reread_performed"] is True
    assert report["offline_replay"]["server_artifact_readback_performed"] is True
    assert report["provenance"]["live_source_artifact_receipt_hash"]
    assert report["provenance"]["source_artifact_receipt_hash"]
    assert report["provenance"]["artifact_ref_hash"]
    assert report["provenance"]["source_identity_hash"]
    assert report["redaction"]["raw_sec_url_returned"] is False
    assert report["redaction"]["raw_storage_path_returned"] is False
    assert report["redaction"]["raw_user_agent_returned"] is False
    assert report["redaction"]["artifact_bytes_returned"] is False
    assert report["redaction"]["raw_fixture_text_returned"] is False
    assert report["non_goals_preserved"]["real_sec_network_request_performed"] is False
    assert report["non_goals_preserved"]["config_default_changed"] is False
    assert report["non_goals_preserved"]["support_matrix_changed"] is False
    assert report["non_goals_preserved"]["default_on_graduation_claimed"] is False
    assert "https://www.sec.gov" not in serialized
    assert "0000320193-24-000123" not in serialized
    assert "0000320193" not in serialized
    assert "320193" not in serialized
    assert "Project6 Offline Replay contact@example.test" not in serialized
    assert str(tmp_path) not in serialized
    assert "SEC-LIVE-REPLAY-RAW-TEXT-MARKER" not in serialized

    receipt_files, artifact_files = _replay_files(runtime_root)
    assert len(receipt_files) == 1
    assert len(artifact_files) == 1
    assert artifact_files[0].read_bytes() == module.FIXTURE_PATH.read_bytes()
    receipt_text = receipt_files[0].read_text(encoding="utf-8")
    assert "https://www.sec.gov" not in receipt_text
    assert "0000320193-24-000123" not in receipt_text
    assert str(tmp_path) not in receipt_text
    assert "SEC-LIVE-REPLAY-RAW-TEXT-MARKER" not in receipt_text


def test_sec_live_replay_uses_fresh_storage_for_reused_runtime_root(tmp_path: Path) -> None:
    module = _replay_module()
    runtime_root = tmp_path / "runtime"

    first = module.build_report(source_root=ROOT, runtime_root=runtime_root)
    second = module.build_report(source_root=ROOT, runtime_root=runtime_root)

    assert first["decision"] == "sec_live_source_artifact_offline_replay_proven"
    assert second["decision"] == "sec_live_source_artifact_offline_replay_proven"
    assert first["offline_replay"]["transport_call_count"] == 1
    assert second["offline_replay"]["transport_call_count"] == 1
    receipt_files, artifact_files = _replay_files(runtime_root)
    assert len(receipt_files) == 2
    assert len(artifact_files) == 2
    assert len({path.parents[2] for path in receipt_files}) == 2


def test_sec_live_replay_restores_prior_live_request_count(tmp_path: Path) -> None:
    module = _replay_module()
    with module.svc._SEC_LIVE_REQUEST_COUNT_LOCK:
        prior_count = module.svc._SEC_LIVE_REQUEST_COUNT
        module.svc._SEC_LIVE_REQUEST_COUNT = 7
    try:
        report = module.build_report(source_root=ROOT, runtime_root=tmp_path / "runtime")
        with module.svc._SEC_LIVE_REQUEST_COUNT_LOCK:
            restored_count = module.svc._SEC_LIVE_REQUEST_COUNT
    finally:
        with module.svc._SEC_LIVE_REQUEST_COUNT_LOCK:
            module.svc._SEC_LIVE_REQUEST_COUNT = prior_count

    assert report["decision"] == "sec_live_source_artifact_offline_replay_proven"
    assert restored_count == 7


def test_sec_live_replay_blocks_empty_fixture_without_transport(tmp_path: Path) -> None:
    module = _replay_module()
    empty_fixture = tmp_path / "empty.txt"
    empty_fixture.write_bytes(b"")

    report = module.build_report(
        source_root=ROOT,
        runtime_root=tmp_path / "runtime",
        fixture_path=empty_fixture,
    )

    assert report["decision"] == "sec_live_source_artifact_offline_replay_blocked"
    assert any(
        item["blocked_reason"] == "sec_live_replay_fixture_missing_or_empty"
        for item in report["blocking_reasons"]
    )
    assert report["offline_replay"]["transport_call_count"] == 0
    assert report["non_goals_preserved"]["real_sec_network_request_performed"] is False


def test_sec_live_replay_blocks_fixture_identity_mismatch_without_transport(tmp_path: Path) -> None:
    module = _replay_module()
    wrong_fixture = tmp_path / "wrong.txt"
    wrong_fixture.write_text("non-empty unrelated SEC replay bytes", encoding="utf-8")

    report = module.build_report(
        source_root=ROOT,
        runtime_root=tmp_path / "runtime",
        fixture_path=wrong_fixture,
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "sec_live_source_artifact_offline_replay_blocked"
    assert any(
        item["blocked_reason"] == "sec_live_replay_fixture_identity_mismatch"
        for item in report["blocking_reasons"]
    )
    assert report["offline_replay"]["transport_call_count"] == 0
    assert report["non_goals_preserved"]["real_sec_network_request_performed"] is False
    assert "non-empty unrelated SEC replay bytes" not in serialized
