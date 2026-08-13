# ruff: noqa: E402
from __future__ import annotations

import hashlib
import os
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    COMMON_GRANT_NON_AUTHORITIES,
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorCampaignLogFileV1,
    ConnectorCampaignLogManifestV1,
    ConnectorCampaignLogSealV1,
    ConnectorEgressArmingIn,
    ConnectorEgressExecuteIn,
    ConnectorEgressGrantV1,
    ConnectorGrantRequestRuleV1,
    DualLiveCampaignDefinitionV1,
    NrcAdamsApsConnectorRunIn,
    NrcApsFreshTargetV1,
    ScienceBaseFreshTargetV1,
)
from app.services.connector_egress_authorization import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    canonical_json_bytes,
    strict_json_loads,
)


CAMPAIGN_ID = "8e51e1fa-32a0-4efd-81bb-27f959f0ae73"
CODE_REVISION = "c" * 40
NOT_BEFORE = "2026-07-30T00:00:00Z"
EXPIRES_AT = "2026-07-30T04:00:00Z"
NOT_BEFORE_DT = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)
EXPIRES_AT_DT = datetime(2026, 7, 30, 4, 0, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_D = "d" * 64


def campaign_payload() -> dict[str, Any]:
    return {
        "schema_id": "project6.dual_live_campaign_definition.v1",
        "campaign_id": CAMPAIGN_ID,
        "code_revision": CODE_REVISION,
        "connector_keys": ["sciencebase_mcs", "nrc_adams_aps"],
        "sciencebase_target": {
            "connector_key": "sciencebase_mcs",
            "item_id": "63d1a3c6d34e06fef15006be",
            "exact_file_name": "mcs2023-germa_salient.csv",
            "locator_key": "downloadUri",
        },
        "nrc_target": {
            "connector_key": "nrc_adams_aps",
            "accession_number": "ML17123A319",
        },
        "acceptance_profile": "dual_live_to_internal_handoff_v1",
        "evidence_profile": "dual_live_evidence_v1",
        "review_policy": "security_egress_and_layer3_integrity_v1",
        "required_review_roles": ["security_egress", "layer3_integrity"],
        "execution_order": "nrc_then_sciencebase",
        "package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        "not_before": NOT_BEFORE,
        "expires_at": EXPIRES_AT,
        "non_authorities": list(CAMPAIGN_NON_AUTHORITIES),
    }


def sciencebase_rules() -> list[dict[str, object]]:
    common = {
        "method": "GET",
        "scheme": "https",
        "port": 443,
        "credential_audience": "none",
    }
    return [
        {
            **common,
            "ordinal": 1,
            "stage": "item_hydration",
            "allowed_hosts": ["www.sciencebase.gov"],
            "path_rule_id": "sciencebase_item_exact_v1",
            "query_rule_id": "format_json_exact_v1",
            "max_response_bytes": 5 * 1024 * 1024,
        },
        {
            **common,
            "ordinal": 2,
            "stage": "artifact",
            "allowed_hosts": ["sciencebase.gov", "www.sciencebase.gov"],
            "path_rule_id": "sciencebase_file_exact_v1",
            "query_rule_id": "sciencebase_exact_file_selector_v1",
            "max_response_bytes": 64 * 1024 * 1024,
        },
        {
            **common,
            "ordinal": 3,
            "stage": "artifact_redirect",
            "allowed_hosts": ["sciencebase.gov", "www.sciencebase.gov"],
            "path_rule_id": "sciencebase_file_exact_v1",
            "query_rule_id": "sciencebase_exact_file_selector_v1",
            "max_response_bytes": 64 * 1024 * 1024,
        },
    ]


def nrc_rules() -> list[dict[str, object]]:
    return [
        {
            "ordinal": 1,
            "stage": "exact_accession_api",
            "method": "GET",
            "scheme": "https",
            "allowed_hosts": ["adams-api.nrc.gov"],
            "port": 443,
            "path_rule_id": "nrc_get_document_exact_v1",
            "query_rule_id": "none_v1",
            "credential_audience": "nrc_aps_api_key",
            "max_response_bytes": 5 * 1024 * 1024,
        },
        {
            "ordinal": 2,
            "stage": "artifact",
            "method": "GET",
            "scheme": "https",
            "allowed_hosts": ["www.nrc.gov"],
            "port": 443,
            "path_rule_id": "nrc_public_pdf_exact_v1",
            "query_rule_id": "none_v1",
            "credential_audience": "none",
            "max_response_bytes": 64 * 1024 * 1024,
        },
    ]


def grant_payload(connector_key: str = "sciencebase_mcs") -> dict[str, Any]:
    sciencebase = connector_key == "sciencebase_mcs"
    return {
        "schema_id": "project6.connector_egress_grant.v1",
        "grant_id": f"grant-{connector_key}-001",
        "connector_key": connector_key,
        "campaign_id": CAMPAIGN_ID,
        "campaign_fingerprint": SHA_A,
        "campaign_definition_sha256": SHA_D,
        "code_revision": CODE_REVISION,
        "arming_nonce": (
            "e571f24e-e703-4c4f-b9c1-0c542a14682c"
            if sciencebase
            else "2725d907-3277-4eb5-9052-ff76c666bfcb"
        ),
        "max_armings": 1,
        "issued_at": NOT_BEFORE,
        "expires_at": EXPIRES_AT,
        "operator_mode": "local_loopback",
        "target": (
            campaign_payload()["sciencebase_target"]
            if sciencebase
            else campaign_payload()["nrc_target"]
        ),
        "request_rules": sciencebase_rules() if sciencebase else nrc_rules(),
        "max_physical_requests": 3 if sciencebase else 2,
        "max_run_bytes": 140 * 1024 * 1024,
        "max_single_send_detection_allowance_bytes": SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
        "request_timeout_seconds": 30,
        "min_request_interval_ms": 250,
        "non_authorities": list(
            COMMON_GRANT_NON_AUTHORITIES if sciencebase else NRC_GRANT_NON_AUTHORITIES
        ),
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (ScienceBaseFreshTargetV1, campaign_payload()["sciencebase_target"]),
        (NrcApsFreshTargetV1, campaign_payload()["nrc_target"]),
        (DualLiveCampaignDefinitionV1, campaign_payload()),
        (ConnectorGrantRequestRuleV1, sciencebase_rules()[0]),
        (ConnectorEgressGrantV1, grant_payload()),
        (
            ConnectorEgressArmingIn,
            {
                "schema_id": "project6.connector_egress_arming.v1",
                "client_request_id": "client-001",
                "connector_key": "sciencebase_mcs",
                "campaign_id": CAMPAIGN_ID,
                "campaign_fingerprint": SHA_A,
                "grant_sha256": SHA_B,
            },
        ),
        (
            ConnectorEgressExecuteIn,
            {
                "execution_idempotency_key": "execute-001",
                "arming_fingerprint": SHA_A,
            },
        ),
    ],
)
def test_new_public_models_forbid_unknown_fields(model, payload) -> None:
    candidate = deepcopy(payload)
    candidate["owner_override"] = "must-not-be-authority"
    with pytest.raises(ValidationError):
        model.model_validate(candidate)


def test_existing_nrc_request_keeps_extra_allow_compatibility() -> None:
    request = NrcAdamsApsConnectorRunIn.model_validate({"future_extension": "preserved"})
    assert request.model_extra == {"future_extension": "preserved"}


def test_campaign_contract_is_exact_and_canonical_bytes_are_stable() -> None:
    model = DualLiveCampaignDefinitionV1.model_validate(campaign_payload())
    first = canonical_json_bytes(model)
    second = canonical_json_bytes(
        DualLiveCampaignDefinitionV1.model_validate(strict_json_loads(first))
    )

    assert first == second
    assert b'"connector_keys":["sciencebase_mcs","nrc_adams_aps"]' in first
    assert b'"not_before":"2026-07-30T00:00:00.000000Z"' in first
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("connector_keys",), ["nrc_adams_aps", "sciencebase_mcs"]),
        (("required_review_roles",), ["layer3_integrity", "security_egress"]),
        (("package_kinds",), ["canonical_internal", "review_facing", "user_facing"]),
        (("expires_at",), NOT_BEFORE),
    ],
)
def test_campaign_rejects_order_or_window_drift(path, replacement) -> None:
    payload = campaign_payload()
    payload[path[0]] = replacement
    with pytest.raises(ValidationError):
        DualLiveCampaignDefinitionV1.model_validate(payload)


def test_sciencebase_grant_normalizes_closed_method_and_hosts() -> None:
    payload = grant_payload()
    payload["request_rules"][0]["method"] = "get"
    payload["request_rules"][0]["allowed_hosts"] = ["WWW.SCIENCEBASE.GOV."]
    grant = ConnectorEgressGrantV1.model_validate(payload)
    assert grant.request_rules[0].method == "GET"
    assert grant.request_rules[0].allowed_hosts == ("www.sciencebase.gov",)


@pytest.mark.parametrize(
    ("mutator",),
    [
        (lambda p: p["request_rules"][0].update(max_response_bytes=1),),
        (lambda p: p.update(max_physical_requests=4),),
        (lambda p: p["request_rules"][1].update(credential_audience="nrc_aps_api_key"),),
        (lambda p: p.update(max_armings=2),),
        (
            lambda p: p.update(
                max_single_send_detection_allowance_bytes=(
                    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES - 1
                )
            ),
        ),
    ],
)
def test_grant_rule_and_budget_drift_fails_closed(mutator) -> None:
    payload = grant_payload()
    mutator(payload)
    with pytest.raises(ValidationError):
        ConnectorEgressGrantV1.model_validate(payload)


def test_nrc_credential_audience_is_bound_to_adams_api_host() -> None:
    payload = grant_payload("nrc_adams_aps")
    payload["request_rules"][0]["allowed_hosts"] = ["www.nrc.gov"]
    with pytest.raises(ValidationError):
        ConnectorEgressGrantV1.model_validate(payload)


def test_duplicate_json_members_and_non_finite_numbers_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        strict_json_loads(b'{"campaign_id":"one","campaign_id":"two"}')
    with pytest.raises(ValueError, match="finite"):
        strict_json_loads(b'{"value":NaN}')


def test_log_contracts_are_strict_and_seal_requires_sorted_extant_runs() -> None:
    log_files = tuple(
        ConnectorCampaignLogFileV1.model_validate(
            {
                "relative_path": f"logs/{SHA_A}/{name}",
                "stream_class": stream_class,
                "byte_count": 0,
                "sha256": SHA_A,
            }
        )
        for name, stream_class in (
            ("app.jsonl", "app"),
            ("http.jsonl", "http"),
            ("stdout.log", "stdout"),
            ("stderr.log", "stderr"),
        )
    )
    manifest = ConnectorCampaignLogManifestV1(
        schema_id="project6.connector_campaign_log_manifest.v1",
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=SHA_A,
        campaign_definition_sha256=SHA_D,
        code_revision=CODE_REVISION,
        runtime_started_at=NOT_BEFORE_DT,
        runtime_stopped_at=EXPIRES_AT_DT,
        files=log_files,
    )
    assert manifest.files == log_files

    bad_manifest = manifest.model_dump(mode="python")
    bad_manifest["files"][0]["relative_path"] = "../app.jsonl"
    with pytest.raises(ValidationError):
        ConnectorCampaignLogManifestV1.model_validate(bad_manifest)

    bad_manifest = manifest.model_dump(mode="python")
    bad_manifest["files"][0]["relative_path"] = (
        f"logs/{SHA_B}/app.jsonl"
    )
    with pytest.raises(ValidationError):
        ConnectorCampaignLogManifestV1.model_validate(bad_manifest)

    with pytest.raises(ValidationError):
        ConnectorCampaignLogSealV1(
            schema_id="project6.connector_campaign_log_seal.v1",
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=SHA_A,
            campaign_definition_sha256=SHA_D,
            campaign_introduction_index_revision=1,
            campaign_introduction_index_sha256=SHA_B,
            code_revision=CODE_REVISION,
            manifest_relative_path=f"logs/{SHA_A}/manifest.json",
            manifest_sha256=SHA_A,
            file_set_hash=SHA_B,
            connector_run_ids=("run-b", "run-a"),
            sealed_at=EXPIRES_AT_DT,
        )

    with pytest.raises(ValidationError):
        ConnectorCampaignLogSealV1(
            schema_id="project6.connector_campaign_log_seal.v1",
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=SHA_A,
            campaign_definition_sha256=SHA_D,
            campaign_introduction_index_revision=1,
            campaign_introduction_index_sha256=SHA_B,
            code_revision=CODE_REVISION,
            manifest_relative_path="../manifest.json",
            manifest_sha256=SHA_A,
            file_set_hash=SHA_B,
            connector_run_ids=("run-a",),
            sealed_at=EXPIRES_AT_DT,
        )
