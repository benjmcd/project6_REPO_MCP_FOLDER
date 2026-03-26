import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "tests"))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base  # noqa: E402
from app.models import ConnectorRun  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_review_packet as review_packet  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_review_packet_contract as contract  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_artifact as challenge  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_artifact_contract as challenge_contract  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact as insight  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact_contract as insight_contract  # noqa: E402
from test_nrc_aps_deterministic_insight_artifact import (  # noqa: E402
    _patch_runtime_settings_all as _patch_runtime_settings_all_insight,
    _persisted_context_dossier,
    _seed_report_index_rows,
    _synthetic_context_packet,
)


def _persisted_insight(db, *, run_id: str) -> dict:
    seeded = _persisted_context_dossier(db, run_id=run_id)
    artifact = insight.assemble_deterministic_insight_artifact(
        db,
        request_payload={
            "context_dossier_ref": seeded["dossier"]["context_dossier_ref"],
            "persist_insight_artifact": True,
        },
    )
    return {"dossier": seeded["dossier"], "insight": artifact}


def _persisted_challenge(db, *, run_id: str) -> dict:
    seeded = _persisted_insight(db, run_id=run_id)
    artifact = challenge.assemble_deterministic_challenge_artifact(
        db,
        request_payload={
            "deterministic_insight_artifact_ref": seeded["insight"]["deterministic_insight_artifact_ref"],
            "persist_challenge_artifact": True,
        },
    )
    return {"dossier": seeded["dossier"], "insight": seeded["insight"], "challenge": artifact}


def _patch_runtime_settings_all(monkeypatch, tmp_path: Path) -> None:
    _patch_runtime_settings_all_insight(monkeypatch, tmp_path)

    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(challenge, "settings", _Settings())
    monkeypatch.setattr(review_packet, "settings", _Settings())


def test_persisted_review_packet_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-review-packet-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        seeded = _persisted_challenge(db, run_id=run_id)
        source_challenge = seeded["challenge"]

        preview = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_id": source_challenge["deterministic_challenge_artifact_id"],
                "persist_review_packet": False,
            },
        )
        first = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_id": source_challenge["deterministic_challenge_artifact_id"],
                "persist_review_packet": True,
            },
        )
        second = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_ref": source_challenge["deterministic_challenge_artifact_ref"],
                "persist_review_packet": True,
            },
        )

        assert first["deterministic_challenge_review_packet_id"] == second["deterministic_challenge_review_packet_id"]
        assert first["deterministic_challenge_review_packet_ref"] == second["deterministic_challenge_review_packet_ref"]
        assert preview["deterministic_challenge_review_packet_id"] == first["deterministic_challenge_review_packet_id"]
        assert Path(first["deterministic_challenge_review_packet_ref"]).exists()

        persisted = review_packet.get_persisted_deterministic_challenge_review_packet(
            deterministic_challenge_review_packet_id=first["deterministic_challenge_review_packet_id"]
        )
        assert persisted["persisted"] is True
        assert persisted["blockers"] == first["blockers"]
        assert persisted["review_items"] == first["review_items"]
        assert persisted["acknowledgements"] == first["acknowledgements"]

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_report_refs") or {})
        assert refs.get("aps_deterministic_challenge_review_packets") == [first["deterministic_challenge_review_packet_ref"]]
        assert refs.get("aps_deterministic_challenge_review_packet_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_deterministic_challenge_review_packet_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["deterministic_challenge_review_packet_id"] == first["deterministic_challenge_review_packet_id"]
    finally:
        db.close()
        engine.dispose()


def test_source_challenge_not_found_invalid_and_ambiguous_behaviors(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)

        with pytest.raises(review_packet.DeterministicChallengeReviewPacketError) as missing_exc:
            review_packet.assemble_deterministic_challenge_review_packet(
                db,
                request_payload={"deterministic_challenge_artifact_id": "missing-challenge", "persist_review_packet": False},
            )
        assert missing_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_NOT_FOUND
        assert missing_exc.value.status_code == 404

        invalid_path = tmp_path / "invalid_challenge.json"
        invalid_path.write_text("{}", encoding="utf-8")
        with pytest.raises(review_packet.DeterministicChallengeReviewPacketError) as invalid_exc:
            review_packet.assemble_deterministic_challenge_review_packet(
                db,
                request_payload={"deterministic_challenge_artifact_ref": str(invalid_path), "persist_review_packet": False},
            )
        assert invalid_exc.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_INVALID
        assert invalid_exc.value.status_code == 422
    finally:
        db.close()
        engine.dispose()


def test_grouped_bucket_correctness(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-review-bucket-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        seeded = _persisted_challenge(db, run_id=run_id)
        source_challenge = seeded["challenge"]

        result = review_packet.assemble_deterministic_challenge_review_packet(
            db,
            request_payload={
                "deterministic_challenge_artifact_ref": source_challenge["deterministic_challenge_artifact_ref"],
                "persist_review_packet": True,
            },
        )

        total = result["total_challenges"]
        assert total == result["blocker_count"] + result["review_item_count"] + result["acknowledgement_count"]
        for blocker in result["blockers"]:
            assert blocker["disposition"] == "block"
        for review_item in result["review_items"]:
            assert review_item["disposition"] == "review"
        for ack in result["acknowledgements"]:
            assert ack["disposition"] == "acknowledge"
    finally:
        db.close()
        engine.dispose()


def test_failure_artifact_recording_on_persist_mode_error(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings_all(monkeypatch, tmp_path)
        run_id = "run-review-failure-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        _persisted_insight(db, run_id=run_id)

        with pytest.raises(review_packet.DeterministicChallengeReviewPacketError):
            review_packet.assemble_deterministic_challenge_review_packet(
                db,
                request_payload={"deterministic_challenge_artifact_id": "missing-challenge", "persist_review_packet": True},
            )

        failure_paths = sorted(tmp_path.glob("*_aps_deterministic_challenge_review_packet_failure_v1.json"))
        assert len(failure_paths) == 0
    finally:
        db.close()
        engine.dispose()
