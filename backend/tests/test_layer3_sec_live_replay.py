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


def test_sec_live_replay_runs_full_mocked_acquire_to_redacted_provenance(tmp_path: Path) -> None:
    module = _replay_module()

    report = module.build_report(source_root=ROOT, runtime_root=tmp_path / "runtime")
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

    storage = tmp_path / "runtime" / "storage" / module.RECEIPT_DIR
    receipt_files = list((storage / "receipts").glob("*.json"))
    artifact_files = list((storage / "artifacts").glob("*.txt"))
    assert len(receipt_files) == 1
    assert len(artifact_files) == 1
    assert artifact_files[0].read_bytes() == module.FIXTURE_PATH.read_bytes()
    receipt_text = receipt_files[0].read_text(encoding="utf-8")
    assert "https://www.sec.gov" not in receipt_text
    assert "0000320193-24-000123" not in receipt_text
    assert str(tmp_path) not in receipt_text
    assert "SEC-LIVE-REPLAY-RAW-TEXT-MARKER" not in receipt_text


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
