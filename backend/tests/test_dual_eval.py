from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.dual_live_evaluator import (
    DualLiveEvaluationError,
    evaluate_dual_live_proof,
)


BACKEND = Path(__file__).resolve().parents[1]
CAMPAIGN_ID = "123e4567-e89b-42d3-a456-426614174000"
CAMPAIGN_FINGERPRINT = "a" * 64
EXPECTED_REPORT = {
    "schema_id": "project6.dual_live_evaluation.v1",
    "campaign_id": CAMPAIGN_ID,
    "expected_campaign_fingerprint": CAMPAIGN_FINGERPRINT,
    "status": "INDETERMINATE",
    "fresh_live": False,
    "evaluation_complete": False,
    "code": "tracked_s3_clearance_and_privileged_runner_required",
    "blocking_dependencies": [
        "tracked_external_s3_clause_5_clearance",
        "privileged_dual_live_runner",
    ],
    "validated_surfaces": [],
    "nonclaims": [
        "no campaign evidence evaluated",
        "no connector run executed",
        "no live acquisition performed",
        "no Layer 3 continuity verdict",
        "no package or handoff verdict",
        "no production readiness claim",
    ],
}


class NoAccess:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"unexpected dependency access: {name}")


def _evaluate(
    *,
    campaign_id: str = CAMPAIGN_ID,
    campaign_fingerprint: str = CAMPAIGN_FINGERPRINT,
) -> dict[str, object]:
    return evaluate_dual_live_proof(
        NoAccess(),
        campaign_id=campaign_id,
        expected_campaign_fingerprint=campaign_fingerprint,
        settings=NoAccess(),
    )


def test_signature_is_the_public_keyword_only_contract() -> None:
    signature = inspect.signature(evaluate_dual_live_proof)

    assert list(signature.parameters) == [
        "db",
        "campaign_id",
        "expected_campaign_fingerprint",
        "settings",
    ]
    assert signature.parameters["db"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature.parameters["campaign_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        signature.parameters["expected_campaign_fingerprint"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    assert signature.parameters["settings"].kind is inspect.Parameter.KEYWORD_ONLY
    assert str(signature.parameters["db"].annotation) == "Session"
    assert str(signature.parameters["settings"].annotation) == "Settings"
    assert str(signature.return_annotation) == "dict[str, Any]"


def test_valid_inputs_return_exact_ordered_indeterminate_report() -> None:
    report = _evaluate()

    assert report == EXPECTED_REPORT
    assert list(report) == list(EXPECTED_REPORT)
    assert report is not EXPECTED_REPORT
    assert report["blocking_dependencies"] is not EXPECTED_REPORT["blocking_dependencies"]
    assert report["nonclaims"] is not EXPECTED_REPORT["nonclaims"]


def test_evaluation_is_repeatable_and_does_not_reuse_mutable_values() -> None:
    first = _evaluate()
    second = _evaluate()

    assert first == second == EXPECTED_REPORT
    assert first is not second
    assert first["blocking_dependencies"] is not second["blocking_dependencies"]
    assert first["validated_surfaces"] is not second["validated_surfaces"]
    assert first["nonclaims"] is not second["nonclaims"]


@pytest.mark.parametrize(
    "campaign_id",
    [
        "",
        " ",
        f" {CAMPAIGN_ID}",
        f"{CAMPAIGN_ID} ",
        CAMPAIGN_ID.upper(),
        "123e4567-e89b-12d3-a456-426614174000",
        "{123e4567-e89b-42d3-a456-426614174000}",
        "urn:uuid:123e4567-e89b-42d3-a456-426614174000",
        "123e4567e89b42d3a456426614174000",
        "not-a-uuid",
    ],
)
def test_campaign_id_must_be_strict_canonical_lowercase_uuid4(
    campaign_id: str,
) -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        _evaluate(campaign_id=campaign_id)

    assert caught.value.code == "dual_live_campaign_id_invalid"


@pytest.mark.parametrize(
    "campaign_fingerprint",
    [
        "",
        " ",
        f" {CAMPAIGN_FINGERPRINT}",
        f"{CAMPAIGN_FINGERPRINT} ",
        "A" * 64,
        "a" * 63,
        "a" * 65,
        ("a" * 63) + "g",
    ],
)
def test_campaign_fingerprint_must_be_strict_lowercase_sha256_hex(
    campaign_fingerprint: str,
) -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        _evaluate(campaign_fingerprint=campaign_fingerprint)

    assert caught.value.code == "dual_live_campaign_fingerprint_invalid"


def test_no_report_value_claims_positive_authority() -> None:
    serialized_values = json.dumps(list(_evaluate().values())).lower()

    for forbidden_claim in (
        '"pass"',
        '"complete"',
        '"valid"',
        '"fresh"',
        '"accepted"',
        '"ready"',
    ):
        assert forbidden_claim not in serialized_values


def test_import_is_inert_and_avoids_runtime_app_dependencies() -> None:
    probe = """
import json
import sys
import app.services.dual_live_evaluator
forbidden = [
    name for name in (
        "app.core.config",
        "app.db.session",
        "sqlalchemy",
    )
    if name in sys.modules
]
print(json.dumps(forbidden))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=BACKEND,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "[]\n"
    assert completed.stderr == ""
