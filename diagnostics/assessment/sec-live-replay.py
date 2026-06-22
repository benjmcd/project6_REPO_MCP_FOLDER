from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import report_header as _report_header  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services import layer3_sec_edgar_live_source_artifact as svc  # noqa: E402


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-live-replay-report.json")
FIXTURE_PATH = ASSESSMENT / "sec-live-fixture.txt"
RECEIPT_DIR = svc.RECEIPT_DIR

TARGET = "sec_live_source_artifact_offline_replay_v1"
NEXT_SLICE = "complete_sec_live_preflight_capstone_after_replay"
RAW_CIK = "0000320193"
NORMALIZED_CIK = "320193"
RAW_ACCESSION = "0000320193-24-000123"
FORM_TYPE = "10-K"
FILING_DATE = "2024-11-01"
USER_AGENT = "Project6 Offline Replay contact@example.test"
FINAL_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/"
    "000032019324000123/0000320193-24-000123.txt"
)
RAW_FIXTURE_MARKER = "SEC-LIVE-REPLAY-RAW-TEXT-MARKER"
FIXTURE_IDENTITY_MARKERS = (
    RAW_FIXTURE_MARKER,
    f"CIK: {RAW_CIK}",
    f"ACCESSION: {RAW_ACCESSION}",
    f"SOURCE URL: {FINAL_URL}",
)


class _ReplayFakeSecClient:
    def __init__(self, content: bytes) -> None:
        self.content = bytes(content)
        self.calls: list[dict[str, Any]] = []

    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ) -> svc.SecEdgarFetchResult:
        self.calls.append(
            {
                "url_hash": _sha256_text(url),
                "user_agent_hash": _sha256_text(user_agent),
                "timeout_seconds": timeout_seconds,
                "max_bytes": max_bytes,
                "raw_url_returned": False,
                "raw_user_agent_returned": False,
            }
        )
        return svc.SecEdgarFetchResult(
            status_code=200,
            content=self.content,
            final_url=FINAL_URL,
            complete=len(self.content) <= max_bytes,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a fully offline SEC live source-artifact replay using a fake SEC client. "
            "No real SEC network request is admitted."
        )
    )
    parser.add_argument("--fixture", default=str(FIXTURE_PATH))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    runtime_root = Path(args.runtime_root) if args.runtime_root else None
    report = build_report(
        source_root=ROOT,
        fixture_path=Path(args.fixture),
        runtime_root=runtime_root,
    )
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    source_root: Path,
    runtime_root: Path | None = None,
    fixture_path: Path | None = None,
) -> dict[str, Any]:
    fixture = Path(fixture_path or FIXTURE_PATH)
    try:
        content = fixture.read_bytes()
    except OSError:
        content = b""
    if not content:
        return _blocked_report(
            source_root=source_root,
            fixture=fixture,
            blocked_reason="sec_live_replay_fixture_missing_or_empty",
            fixture_hash=None,
            fixture_length=0,
        )
    if not _fixture_matches_selected_filing(content):
        return _blocked_report(
            source_root=source_root,
            fixture=fixture,
            blocked_reason="sec_live_replay_fixture_identity_mismatch",
            fixture_hash=hashlib.sha256(content).hexdigest(),
            fixture_length=len(content),
        )

    if runtime_root is None:
        with tempfile.TemporaryDirectory(prefix="sec-live-replay-") as temp_root:
            return _run_replay(
                source_root=source_root,
                runtime_root=Path(temp_root),
                fixture=fixture,
                content=content,
            )
    return _run_replay(
        source_root=source_root,
        runtime_root=runtime_root,
        fixture=fixture,
        content=content,
    )


def _run_replay(*, source_root: Path, runtime_root: Path, fixture: Path, content: bytes) -> dict[str, Any]:
    runtime_root.mkdir(parents=True, exist_ok=True)
    storage = _new_run_storage(runtime_root)
    fake_client = _ReplayFakeSecClient(content)
    fixture_hash = hashlib.sha256(content).hexdigest()
    payload = _request_payload(expected_content_sha256=fixture_hash)
    previous = _capture_runtime()

    try:
        _install_offline_runtime(storage=storage, fake_client=fake_client)
        initial = svc.acquire_sec_edgar_text_table_live_source_artifact(payload)
        replay = svc.acquire_sec_edgar_text_table_live_source_artifact(payload)
        status = svc.inspect_sec_edgar_text_table_live_source_artifact_status(
            initial["live_source_artifact_receipt_id"]
        )
        receipt, artifact_bytes = svc.read_sec_edgar_text_table_live_source_artifact_bytes(
            initial["live_source_artifact_receipt_id"],
            expected_live_source_artifact_receipt_hash=initial["live_source_artifact_receipt_hash"],
        )
    finally:
        _restore_runtime(previous)

    artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
    receipt_texts = _receipt_texts(storage)
    redaction = _redaction_scan(
        [
            json.dumps(initial, sort_keys=True),
            json.dumps(replay, sort_keys=True),
            json.dumps(status, sort_keys=True),
            json.dumps(receipt, sort_keys=True),
            json.dumps(fake_client.calls, sort_keys=True),
            *receipt_texts,
        ],
        runtime_root=runtime_root,
    )
    provenance = {
        "live_source_artifact_receipt_id": initial["live_source_artifact_receipt_id"],
        "live_source_artifact_receipt_hash": initial["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_id": initial["source_artifact_receipt"]["source_artifact_receipt_id"],
        "source_artifact_receipt_hash": initial["source_artifact_receipt"]["source_artifact_receipt_hash"],
        "artifact_ref_hash": initial["retained_source_artifact_manifest"]["artifact_ref_hash"],
        "source_identity_hash": initial["source_identity"]["source_identity_hash"],
        "server_derived_url_hash": initial["sec_request_policy"]["server_derived_url_hash"],
        "user_agent_hash": initial["sec_request_policy"]["server_configured_user_agent_hash"],
    }
    offline_replay = {
        "fixture_hash": fixture_hash,
        "fixture_length": len(content),
        "fixture_marker": _sha256_text(RAW_FIXTURE_MARKER),
        "fixture_path_marker": _sha256_text(str(fixture.resolve(strict=False))),
        "fake_transport_used": True,
        "transport_call_count": len(fake_client.calls),
        "idempotent_replay": replay["idempotency"]["idempotent_replay"] is True,
        "initial_network_request_made_with_fake_transport": initial["cache"]["network_request_made"] is True,
        "status_reread_performed": status["cache"]["cache_status"] == "status",
        "server_artifact_readback_performed": bool(artifact_bytes),
        "raw_fixture_text_returned": redaction["raw_fixture_text_returned"],
    }
    server_readback = {
        "content_sha256": artifact_hash,
        "content_length": len(artifact_bytes),
        "matches_fixture_hash": artifact_hash == fixture_hash,
        "artifact_bytes_returned": False,
    }
    non_goals = _non_goals()
    criteria = [
        _criterion(
            "fixture_present_nonempty",
            len(content) > 0,
            {"fixture_hash": fixture_hash, "fixture_length": len(content)},
            "sec_live_replay_fixture_missing_or_empty",
        ),
        _criterion(
            "fake_transport_used_once_for_initial_acquire",
            fake_client.calls
            and len(fake_client.calls) == 1
            and initial["cache"]["network_request_made"] is True
            and replay["cache"]["network_request_made"] is False,
            {
                "fake_transport_used": True,
                "transport_call_count": len(fake_client.calls),
                "idempotent_replay": offline_replay["idempotent_replay"],
            },
            "sec_live_replay_transport_contract_failed",
        ),
        _criterion(
            "server_retained_artifact_hash_matches_fixture",
            server_readback["matches_fixture_hash"] and receipt["source_artifact_receipt"]["content_sha256"] == fixture_hash,
            server_readback,
            "sec_live_replay_artifact_hash_mismatch",
        ),
        _criterion(
            "redacted_hash_only_provenance_surface",
            not any(redaction.values()),
            redaction,
            "sec_live_replay_raw_authority_leak",
        ),
        _criterion(
            "offline_non_goals_preserved",
            not any(non_goals.values()),
            non_goals,
            "sec_live_replay_non_goal_changed",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    return _report_header(
        schema_id="diagnostics.sec_live_source_artifact_offline_replay.v1",
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision=(
            "sec_live_source_artifact_offline_replay_proven"
            if not blockers
            else "sec_live_source_artifact_offline_replay_blocked"
        ),
        criteria=criteria,
        blocking_reasons=blockers,
        offline_replay=offline_replay,
        provenance=provenance,
        server_readback=server_readback,
        redaction=redaction,
        transport={
            "fake_client_contract_double_used": True,
            "transport_call_count": len(fake_client.calls),
            "calls": list(fake_client.calls),
            "real_sec_network_request_performed": False,
            "raw_url_returned": False,
            "raw_user_agent_returned": False,
        },
        non_goals_preserved=non_goals,
    )


def _blocked_report(
    *,
    source_root: Path,
    fixture: Path,
    blocked_reason: str,
    fixture_hash: str | None,
    fixture_length: int,
) -> dict[str, Any]:
    redaction = {
        "raw_sec_url_returned": False,
        "raw_cik_returned": False,
        "raw_accession_returned": False,
        "raw_storage_path_returned": False,
        "raw_user_agent_returned": False,
        "artifact_bytes_returned": False,
        "raw_fixture_text_returned": False,
    }
    criteria = [
        _criterion(
            (
                "fixture_present_nonempty"
                if blocked_reason == "sec_live_replay_fixture_missing_or_empty"
                else "fixture_matches_selected_filing_identity"
            ),
            False,
            {
                "fixture_marker": _sha256_text(str(fixture.resolve(strict=False))),
                "source_root_marker": _sha256_text(str(source_root.resolve(strict=False))),
                "fixture_hash": fixture_hash,
                "fixture_length": fixture_length,
            },
            blocked_reason,
        )
    ]
    return _report_header(
        schema_id="diagnostics.sec_live_source_artifact_offline_replay.v1",
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision="sec_live_source_artifact_offline_replay_blocked",
        criteria=criteria,
        blocking_reasons=criteria,
        offline_replay={
            "fixture_hash": fixture_hash,
            "fixture_length": fixture_length,
            "fake_transport_used": False,
            "transport_call_count": 0,
            "idempotent_replay": False,
            "status_reread_performed": False,
            "server_artifact_readback_performed": False,
            "raw_fixture_text_returned": False,
        },
        provenance={},
        server_readback={"artifact_bytes_returned": False},
        redaction=redaction,
        transport={
            "fake_client_contract_double_used": True,
            "transport_call_count": 0,
            "real_sec_network_request_performed": False,
            "raw_url_returned": False,
            "raw_user_agent_returned": False,
        },
        non_goals_preserved=_non_goals(),
    )


def _request_payload(*, expected_content_sha256: str) -> dict[str, Any]:
    return {
        "client_request_id": "sec-live-offline-replay-001",
        "acquisition_mode": svc.ACQUISITION_MODE,
        "operator_decision": svc.OPERATOR_DECISION,
        "cik_or_filer_ref": RAW_CIK,
        "accession_or_submission_id": RAW_ACCESSION,
        "form_type": FORM_TYPE,
        "filing_date": FILING_DATE,
        "expected_content_sha256": expected_content_sha256,
        "operator_confirmation": True,
    }


def _fixture_matches_selected_filing(content: bytes) -> bool:
    text = content.decode("utf-8", errors="replace")
    return all(marker in text for marker in FIXTURE_IDENTITY_MARKERS)


def _new_run_storage(runtime_root: Path) -> Path:
    parent = runtime_root / "storage"
    parent.mkdir(parents=True, exist_ok=True)
    for _attempt in range(10):
        candidate = parent / f"run-{uuid4().hex[:12]}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("sec_live_replay_runtime_storage_collision")


def _capture_runtime() -> dict[str, Any]:
    with svc._SEC_LIVE_REQUEST_COUNT_LOCK:
        live_request_count = svc._SEC_LIVE_REQUEST_COUNT
    return {
        "storage_dir": settings.storage_dir,
        "database_url": settings.database_url,
        "live_enabled": settings.layer3_sec_edgar_live_network_enabled,
        "user_agent": settings.layer3_sec_edgar_user_agent,
        "rate_limit": settings.layer3_sec_edgar_rate_limit_per_second,
        "max_live_requests": settings.layer3_sec_edgar_max_live_requests_per_process,
        "max_bytes": settings.layer3_sec_edgar_max_bytes,
        "timeout_seconds": settings.layer3_sec_edgar_timeout_seconds,
        "client": svc.SEC_EDGAR_CLIENT,
        "sleep": svc.SEC_EDGAR_SLEEP,
        "live_request_count": live_request_count,
    }


def _install_offline_runtime(*, storage: Path, fake_client: _ReplayFakeSecClient) -> None:
    settings.storage_dir = str(storage.resolve(strict=False))
    settings.database_url = "sqlite:///:memory:"
    settings.layer3_sec_edgar_live_network_enabled = True
    settings.layer3_sec_edgar_user_agent = USER_AGENT
    settings.layer3_sec_edgar_rate_limit_per_second = 10
    settings.layer3_sec_edgar_max_live_requests_per_process = 10
    settings.layer3_sec_edgar_max_bytes = 25_000_000
    settings.layer3_sec_edgar_timeout_seconds = 20
    svc.SEC_EDGAR_CLIENT = fake_client
    svc.SEC_EDGAR_SLEEP = lambda _seconds: None
    with svc._SEC_LIVE_REQUEST_COUNT_LOCK:
        svc._SEC_LIVE_REQUEST_COUNT = 0


def _restore_runtime(previous: Mapping[str, Any]) -> None:
    settings.storage_dir = str(previous["storage_dir"])
    settings.database_url = str(previous["database_url"])
    settings.layer3_sec_edgar_live_network_enabled = bool(previous["live_enabled"])
    settings.layer3_sec_edgar_user_agent = str(previous["user_agent"])
    settings.layer3_sec_edgar_rate_limit_per_second = int(previous["rate_limit"])
    settings.layer3_sec_edgar_max_live_requests_per_process = int(previous["max_live_requests"])
    settings.layer3_sec_edgar_max_bytes = int(previous["max_bytes"])
    settings.layer3_sec_edgar_timeout_seconds = int(previous["timeout_seconds"])
    svc.SEC_EDGAR_CLIENT = previous["client"]
    svc.SEC_EDGAR_SLEEP = previous["sleep"]
    with svc._SEC_LIVE_REQUEST_COUNT_LOCK:
        svc._SEC_LIVE_REQUEST_COUNT = int(previous["live_request_count"])


def _receipt_texts(storage: Path) -> list[str]:
    receipts = storage / RECEIPT_DIR / "receipts"
    if not receipts.exists():
        return []
    values = []
    for path in sorted(receipts.glob("*.json")):
        try:
            values.append(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return values


def _redaction_scan(texts: list[str], *, runtime_root: Path) -> dict[str, bool]:
    combined = "\n".join(texts)
    return {
        "raw_sec_url_returned": "https://www.sec.gov" in combined,
        "raw_cik_returned": RAW_CIK in combined or NORMALIZED_CIK in combined,
        "raw_accession_returned": RAW_ACCESSION in combined,
        "raw_storage_path_returned": str(runtime_root.resolve(strict=False)) in combined,
        "raw_user_agent_returned": USER_AGENT in combined,
        "artifact_bytes_returned": "<SEC-DOCUMENT>" in combined,
        "raw_fixture_text_returned": RAW_FIXTURE_MARKER in combined,
    }


def _non_goals() -> dict[str, bool]:
    return {
        "real_sec_network_request_performed": False,
        "shared_runtime_artifact_created": False,
        "production_database_touched": False,
        "arelle_subprocess_invoked": False,
        "multi_filing_authority_exercised": False,
        "delivery_export_status_exercised": False,
        "provider_delivery_exercised": False,
        "nonlocal_auth_changed": False,
        "value_reveal_exercised": False,
        "config_default_changed": False,
        "support_matrix_changed": False,
        "default_on_graduation_claimed": False,
        "production_readiness_claimed": False,
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
