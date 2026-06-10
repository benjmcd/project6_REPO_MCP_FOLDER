from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from fastapi.testclient import TestClient
import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_candidate_b_operator_workflow_access_policy as access_policy
from app.services import layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint as acceptance
from app.services import layer3_candidate_b_full_corpus_repeatability_acceptance_closeout as closeout
from app.services import layer3_candidate_b_full_corpus_repeatability_rerun_trial as rerun_trial
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status
from main import app
from test_layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint import (
    _acceptance_request,
    _rerun_request,
    acceptance_authority,
)


ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout"
STATUS_ENDPOINT = f"{ENDPOINT}/status"


def _acceptance_receipt(checkpoint_receipt: dict[str, Any]) -> dict[str, Any]:
    rerun_receipt = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(
        _rerun_request(checkpoint_receipt)
    )
    return acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
        _acceptance_request(checkpoint_receipt, rerun_receipt)
    )


def _closeout_request(
    acceptance_receipt: dict[str, Any],
    *,
    client_request_id: str = "acceptance-closeout",
    acceptance_disposition: str = "no_regression_observed",
) -> dict[str, Any]:
    assert (
        closeout.RENDERED_CONTROL_MODE
        == "rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control"
    )
    return {
        "client_request_id": client_request_id,
        "acceptance_closeout_mode": closeout.CLOSEOUT_MODE,
        "operator_decision": closeout.OPERATOR_DECISION,
        "repeatability_acceptance_checkpoint_receipt_id": acceptance_receipt[
            "repeatability_acceptance_checkpoint_receipt_id"
        ],
        "repeatability_acceptance_checkpoint_receipt_hash": acceptance_receipt[
            "repeatability_acceptance_checkpoint_receipt_hash"
        ],
        "repeatability_acceptance_checkpoint_hash": acceptance_receipt[
            "repeatability_acceptance_checkpoint_hash"
        ],
        "repeatability_acceptance_checkpoint_authority_hash": acceptance_receipt[
            "repeatability_acceptance_checkpoint_authority_hash"
        ],
        "acceptance_disposition": acceptance_disposition,
        "rendered_acceptance_control_mode": closeout.RENDERED_CONTROL_MODE,
        "rendered_acceptance_control_proof_state": closeout.RENDERED_PROOF_STATE,
        "headless_rendered_proof_label": closeout.HEADLESS_RENDERED_PROOF_LABEL,
        "headed_rendered_proof_label": closeout.HEADED_RENDERED_PROOF_LABEL,
        "operator_runbook_closeout_steps": list(closeout.REQUIRED_RUNBOOK_STEPS),
        "negative_invariant_attestations": dict(closeout.REQUIRED_NEGATIVE_INVARIANTS),
    }


def _status_request(**overrides: str) -> dict[str, str]:
    payload = {
        "client_request_id": "acceptance-closeout-status",
        "closeout_status_mode": closeout.STATUS_MODE,
        "operator_decision": closeout.STATUS_OPERATOR_DECISION,
    }
    payload.update(overrides)
    return payload


def _stored_receipt_path(root: Path, receipt_id: str) -> Path:
    return root / receipt_id / "receipt.json"


def _strip_top_level_owner_binding(path: Path, receipt_hash_key: str) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt.pop("workflow_receipt_owner_binding", None)
    receipt[receipt_hash_key] = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {receipt_hash_key, "server_time"}}
    )
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def _proxy_owner_binding(actor: str, tenant: str, policy_hash: str) -> dict[str, str]:
    return {
        "actor_ref_hash": access_policy._stable_hash({"auth_owner": "proxy", "actor_ref": actor}),
        "tenant_or_workspace_ref_hash": access_policy._stable_hash(
            {"auth_owner": "proxy", "tenant_or_workspace_ref": tenant}
        ),
        "policy_hash": policy_hash,
    }


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_records_append_only(
    acceptance_authority: dict[str, Any],
) -> None:
    checkpoint_receipt = acceptance_authority["checkpoint_receipt"]
    acceptance_receipt = _acceptance_receipt(checkpoint_receipt)

    response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )

    assert response["repeatability_acceptance_operator_closeout_state"] == closeout.CLOSEOUT_STATE
    assert response["append_only_repeatability_acceptance_operator_closeout_receipt"] is True
    assert response["repeatability_acceptance_checkpoint_receipt_mutated"] is False
    assert response["original_repeatability_checkpoint_receipt_mutated"] is False
    assert response["repeatability_rerun_trial_receipt_mutated"] is False
    assert response["baseline_rollback_preserved"] is True
    assert response["candidate_a_semantics_preserved"] is True
    assert response["candidate_b_default_scope_preserved"] == "eligible_effective_pdfs_only"
    assert response["negative_invariants"] == dict(closeout.REQUIRED_NEGATIVE_INVARIANTS)
    receipt_path = (
        acceptance_authority["root"]
        / response["repeatability_acceptance_operator_closeout_receipt_id"]
        / "receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["repeatability_acceptance_operator_closeout_receipt_hash"]
    assert receipt["workflow_receipt_owner_binding"]
    assert "workflow_receipt_owner_binding" not in receipt["repeatability_acceptance_operator_closeout"]
    assert (
        receipt["repeatability_acceptance_operator_closeout"]["rendered_acceptance_control_proof"][
            "rendered_acceptance_control_proof_state"
        ]
        == closeout.RENDERED_PROOF_STATE
    )


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_ignores_policy_hash_for_same_owner(
    acceptance_authority: dict[str, Any],
) -> None:
    rows = acceptance_authority["rows"]
    rows["cb-full-corpus-operator-original"]["ownership_access_policy"]["policy_hash"] = "1" * 64
    rows["cb-full-corpus-operator-rerun"]["ownership_access_policy"]["policy_hash"] = "2" * 64
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])

    response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )

    assert response["repeatability_acceptance_operator_closeout_state"] == closeout.CLOSEOUT_STATE
    assert response["workflow_receipt_owner_binding"]["policy_hash"] == "1" * 64


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_preserves_authority_identity(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])

    response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )

    closeout_body = response["repeatability_acceptance_operator_closeout"]
    expected_closeout_hash = workflow_status._stable_hash(closeout_body)
    expected_authority = {
        **closeout_body,
        "operator_decision": closeout.OPERATOR_DECISION,
        "repeatability_acceptance_operator_closeout_hash": expected_closeout_hash,
    }
    assert "workflow_receipt_owner_binding" not in closeout_body
    assert "workflow_receipt_owner_binding" not in response[
        "repeatability_acceptance_operator_closeout_authority"
    ]
    assert response["repeatability_acceptance_operator_closeout_hash"] == expected_closeout_hash
    assert response["repeatability_acceptance_operator_closeout_authority_hash"] == workflow_status._stable_hash(
        expected_authority
    )
    assert response["workflow_receipt_owner_binding"]


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_projects_not_recorded(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])

    response = closeout.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
        _status_request(
            repeatability_acceptance_checkpoint_receipt_id=acceptance_receipt[
                "repeatability_acceptance_checkpoint_receipt_id"
            ],
            repeatability_acceptance_checkpoint_receipt_hash=acceptance_receipt[
                "repeatability_acceptance_checkpoint_receipt_hash"
            ],
            repeatability_acceptance_checkpoint_authority_hash=acceptance_receipt[
                "repeatability_acceptance_checkpoint_authority_hash"
            ],
        )
    )

    assert response["status"] == "available"
    assert response["closeout_status_projection_state"] == "not_recorded"
    assert response["repeatability_acceptance_operator_closeout_receipt_available"] is False
    assert response["operator_projection"]["read_only_acceptance_closeout_status_projection"] is True
    assert response["operator_projection"]["closeout_status_policy_enforced"] is True
    assert response["operator_projection"]["review_status_projection_policy_enforced"] is True
    assert response["operator_projection"]["audit_projection_policy_enforced"] is True
    assert response["operator_projection"]["acceptance_closeout_receipt_creation_admitted_now"] is False
    assert response["operator_projection"]["frontend_durable_authority_enabled"] is False
    assert response["operator_projection"]["default_scope_expansion_admitted"] is False
    assert response["ownership_access_policy"]["projection_authority_kind"] == (
        "repeatability_acceptance_checkpoint_selector"
    )
    assert response["ownership_access_policy"]["protected_route_families"] == [
        "closeout_status",
        "review_status_projection",
        "audit_projection",
    ]
    assert response["ownership_access_policy"]["closeout_status"]["route_family"] == "closeout_status"
    assert (
        response["ownership_access_policy"]["review_status_projection"]["route_family"]
        == "review_status_projection"
    )
    assert response["ownership_access_policy"]["audit_projection"]["route_family"] == "audit_projection"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_rejects_missing_checkpoint(
    acceptance_authority: dict[str, Any],
) -> None:
    missing_receipt_id = f"{acceptance.ACCEPTANCE_CHECKPOINT_RECEIPT_PREFIX}-ffffffffffffffffffffffff"

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
            _status_request(
                repeatability_acceptance_checkpoint_receipt_id=missing_receipt_id,
                repeatability_acceptance_checkpoint_receipt_hash="1" * 64,
                repeatability_acceptance_checkpoint_authority_hash="2" * 64,
            )
        )

    assert exc_info.value.http_status == 404
    assert exc_info.value.code == (
        "candidate_b_full_corpus_repeatability_acceptance_closeout_acceptance_checkpoint_missing"
    )
    assert acceptance_authority["root"].is_dir()


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_projects_available(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    closeout_response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )

    response = closeout.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
        _status_request(
            repeatability_acceptance_checkpoint_receipt_id=acceptance_receipt[
                "repeatability_acceptance_checkpoint_receipt_id"
            ],
            repeatability_acceptance_checkpoint_receipt_hash=acceptance_receipt[
                "repeatability_acceptance_checkpoint_receipt_hash"
            ],
            repeatability_acceptance_checkpoint_authority_hash=acceptance_receipt[
                "repeatability_acceptance_checkpoint_authority_hash"
            ],
        )
    )

    assert response["closeout_status_projection_state"] == "available"
    assert response["repeatability_acceptance_operator_closeout_receipt_available"] is True
    assert response["repeatability_acceptance_operator_closeout_receipt_id"] == closeout_response[
        "repeatability_acceptance_operator_closeout_receipt_id"
    ]
    assert response["repeatability_acceptance_operator_closeout_receipt_hash"] == closeout_response[
        "repeatability_acceptance_operator_closeout_receipt_hash"
    ]
    assert response["repeatability_acceptance_operator_closeout_receipt_ref"].startswith(
        "candidate-b-full-corpus-operator-workflow-repeatability-acceptance-closeout://"
    )
    assert response["rendered_acceptance_control_proof_state"] == closeout.RENDERED_PROOF_STATE
    assert response["negative_invariants"] == dict(closeout.REQUIRED_NEGATIVE_INVARIANTS)
    assert response["operator_projection"]["closeout_receipt_projection_visible"] is True
    assert response["operator_projection"]["acceptance_closeout_receipt_mutation_admitted"] is False
    assert response["operator_projection"]["actual_corpus_processing_execution_admitted_now"] is False
    assert response["operator_projection"]["provider_object_write_enabled"] is False
    assert response["ownership_access_policy"]["projection_authority_kind"] == (
        "repeatability_acceptance_operator_closeout_receipt"
    )
    assert response["ownership_access_policy"]["protected_route_families"] == [
        "closeout_status",
        "review_status_projection",
        "audit_projection",
    ]
    for route_family in response["ownership_access_policy"]["protected_route_families"]:
        policy = response["ownership_access_policy"][route_family]
        assert policy["route_family"] == route_family
        assert policy["policy_status"] == "admitted"
        assert policy["audit_event_ref"].startswith("candidate-b-operator-workflow-policy://")
        assert policy["raw_operator_identity_exposed"] is False
        assert policy["raw_local_path_exposed"] is False
        audit_path = acceptance_authority["root"] / policy["audit_event_id"] / "receipt.json"
        audit_receipt = json.loads(audit_path.read_text(encoding="utf-8"))
        assert audit_receipt["route_family"] == route_family
        assert audit_receipt["raw_proxy_header_exposed"] is False
        assert audit_receipt["raw_url_exposed"] is False


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_reads_legacy_acceptance_under_proxy(
    acceptance_authority: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    legacy_acceptance_receipt = _strip_top_level_owner_binding(
        _stored_receipt_path(
            acceptance_authority["root"],
            acceptance_receipt["repeatability_acceptance_checkpoint_receipt_id"],
        ),
        "repeatability_acceptance_checkpoint_receipt_hash",
    )
    rows = acceptance_authority["rows"]
    rows["cb-full-corpus-operator-original"]["ownership_access_policy"] = _proxy_owner_binding(
        "alice", "tenant-a", "1" * 64
    )
    rows["cb-full-corpus-operator-rerun"]["ownership_access_policy"] = _proxy_owner_binding(
        "alice", "tenant-a", "2" * 64
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)

    with access_policy.request_context(
        {"X-Forwarded-User": "alice", "X-Forwarded-Groups": "tenant-a"}
    ):
        response = closeout.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
            _status_request(
                operator_role="auditor",
                repeatability_acceptance_checkpoint_receipt_id=legacy_acceptance_receipt[
                    "repeatability_acceptance_checkpoint_receipt_id"
                ],
                repeatability_acceptance_checkpoint_receipt_hash=legacy_acceptance_receipt[
                    "repeatability_acceptance_checkpoint_receipt_hash"
                ],
                repeatability_acceptance_checkpoint_authority_hash=legacy_acceptance_receipt[
                    "repeatability_acceptance_checkpoint_authority_hash"
                ],
            )
        )

    assert response["closeout_status_projection_state"] == "not_recorded"
    assert response["ownership_access_policy"]["closeout_status"]["decision"] == "allow"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_reads_legacy_closeout_under_proxy(
    acceptance_authority: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    closeout_response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )
    legacy_closeout_receipt = _strip_top_level_owner_binding(
        _stored_receipt_path(
            acceptance_authority["root"],
            closeout_response["repeatability_acceptance_operator_closeout_receipt_id"],
        ),
        "repeatability_acceptance_operator_closeout_receipt_hash",
    )
    rows = acceptance_authority["rows"]
    rows["cb-full-corpus-operator-original"]["ownership_access_policy"] = _proxy_owner_binding(
        "alice", "tenant-a", "1" * 64
    )
    rows["cb-full-corpus-operator-rerun"]["ownership_access_policy"] = _proxy_owner_binding(
        "alice", "tenant-a", "2" * 64
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)

    with access_policy.request_context(
        {"X-Forwarded-User": "alice", "X-Forwarded-Groups": "tenant-a"}
    ):
        response = closeout.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
            _status_request(
                operator_role="auditor",
                repeatability_acceptance_operator_closeout_receipt_id=legacy_closeout_receipt[
                    "repeatability_acceptance_operator_closeout_receipt_id"
                ],
                repeatability_acceptance_operator_closeout_receipt_hash=legacy_closeout_receipt[
                    "repeatability_acceptance_operator_closeout_receipt_hash"
                ],
            )
        )

    assert response["closeout_status_projection_state"] == "available"
    assert response["ownership_access_policy"]["closeout_status"]["decision"] == "allow"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_api_accepts_closeout_mode(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    app.openapi_schema = None
    with TestClient(app) as test_client:
        closeout_response = test_client.post(ENDPOINT, json=_closeout_request(acceptance_receipt))
        assert closeout_response.status_code == 200, closeout_response.text
        closeout_body = closeout_response.json()
        status_response = test_client.post(
            STATUS_ENDPOINT,
            json=_status_request(
                operator_role="auditor",
                repeatability_acceptance_operator_closeout_receipt_id=closeout_body[
                    "repeatability_acceptance_operator_closeout_receipt_id"
                ],
                repeatability_acceptance_operator_closeout_receipt_hash=closeout_body[
                    "repeatability_acceptance_operator_closeout_receipt_hash"
                ],
            ),
        )
        assert status_response.status_code == 200, status_response.text
    app.openapi_schema = None

    status_body = status_response.json()
    assert status_body["closeout_status_projection_state"] == "available"
    assert status_body["repeatability_acceptance_operator_closeout_receipt_id"] == closeout_body[
        "repeatability_acceptance_operator_closeout_receipt_id"
    ]
    assert status_body["operator_projection"]["read_only_acceptance_closeout_status_projection"] is True
    assert status_body["ownership_access_policy"]["closeout_status"]["route_family"] == "closeout_status"
    assert status_body["ownership_access_policy"]["closeout_status"]["decision"] == "allow"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_api_rejects_proxy_missing_identity(
    acceptance_authority: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    closeout_response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    app.openapi_schema = None
    with TestClient(app) as test_client:
        status_response = test_client.post(
            STATUS_ENDPOINT,
            json=_status_request(
                repeatability_acceptance_operator_closeout_receipt_id=closeout_response[
                    "repeatability_acceptance_operator_closeout_receipt_id"
                ],
                repeatability_acceptance_operator_closeout_receipt_hash=closeout_response[
                    "repeatability_acceptance_operator_closeout_receipt_hash"
                ],
            ),
        )
    app.openapi_schema = None

    assert status_response.status_code == 401
    body = status_response.json()
    assert body["status"] == "blocked"
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_status_rejects_stale_hash(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    closeout_response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
            _status_request(
                repeatability_acceptance_operator_closeout_receipt_id=closeout_response[
                    "repeatability_acceptance_operator_closeout_receipt_id"
                ],
                repeatability_acceptance_operator_closeout_receipt_hash="0" * 64,
            )
        )

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_repeatability_acceptance_closeout_status_stale_closeout_receipt"
    )


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_is_idempotent(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    payload = _closeout_request(acceptance_receipt)

    first = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)
    second = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)

    assert second["idempotent_replay"] is True
    assert second["repeatability_acceptance_operator_closeout_receipt_id"] == first[
        "repeatability_acceptance_operator_closeout_receipt_id"
    ]


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_blocks_regression(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    receipt_path = (
        acceptance_authority["root"]
        / acceptance_receipt["repeatability_acceptance_checkpoint_receipt_id"]
        / "receipt.json"
    )
    mutated = json.loads(receipt_path.read_text(encoding="utf-8"))
    checkpoint = dict(mutated["repeatability_acceptance_checkpoint"])
    checkpoint["acceptance_disposition"] = acceptance.BLOCKED_DISPOSITION
    checkpoint_hash = workflow_status._stable_hash(checkpoint)
    authority = {
        **checkpoint,
        "operator_decision": acceptance.OPERATOR_DECISION,
        "repeatability_acceptance_checkpoint_hash": checkpoint_hash,
    }
    mutated["repeatability_acceptance_checkpoint"] = checkpoint
    mutated["repeatability_acceptance_checkpoint_hash"] = checkpoint_hash
    mutated["repeatability_acceptance_checkpoint_authority"] = authority
    mutated["repeatability_acceptance_checkpoint_authority_hash"] = workflow_status._stable_hash(authority)
    mutated["repeatability_acceptance_checkpoint_receipt_hash"] = workflow_status._stable_hash(
        {
            key: value
            for key, value in mutated.items()
            if key not in {"repeatability_acceptance_checkpoint_receipt_hash", "server_time"}
        }
    )
    receipt_path.write_text(json.dumps(mutated, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
            _closeout_request(
                mutated,
                client_request_id="acceptance-closeout-blocked",
                acceptance_disposition=acceptance.BLOCKED_DISPOSITION,
            )
        )

    assert exc_info.value.code == "candidate_b_full_corpus_repeatability_acceptance_closeout_regression_detected"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_rejects_ambiguous_rendered_proof(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    payload = _closeout_request(acceptance_receipt)
    payload["rendered_acceptance_control_proof_state"] = "headless_only"

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_proof_ambiguous"
    )


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_rejects_raw_authority(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    payload = _closeout_request(acceptance_receipt)
    payload["path"] = "C:\\raw\\path"

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_repeatability_acceptance_closeout_forbidden_request_fields"
    )
