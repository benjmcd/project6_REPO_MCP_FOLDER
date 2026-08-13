# ruff: noqa: E402
from __future__ import annotations

from collections.abc import Callable
import hashlib
import inspect
import os
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from starlette.requests import Request

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import Settings, settings
from app.schemas.api import (
    CAMPAIGN_NON_AUTHORITIES,
    COMMON_GRANT_NON_AUTHORITIES,
    NRC_GRANT_NON_AUTHORITIES,
    ConnectorCampaignEvidenceIndexV1,
    ConnectorGrantConsumptionMarkerV1,
    ConnectorEgressGrantV1,
    DualLiveCampaignDefinitionV1,
)
from app.services import connector_egress_authorization as egress_auth
from app.services import dual_live_windows
from app.services.connector_egress_authorization import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    ConnectorEgressAuthorizationError,
    VerifiedHistoricalGrantEvidence,
    authorize_connector_egress_owner,
    canonical_json_bytes,
    load_evidence_index_chain_read_only,
    resolve_current_connector_egress_grant,
    resolve_current_dual_live_campaign_definition,
    resolve_historical_connector_grant_evidence,
    resolve_historical_connector_grant_evidence_read_only,
)


CAMPAIGN_ID = "8e51e1fa-32a0-4efd-81bb-27f959f0ae73"
SECOND_CAMPAIGN_ID = "d5211c64-2c37-4f21-9c40-b72ccb77d406"
CODE_REVISION = "c" * 40
NOW = datetime(2026, 7, 30, 1, 0, tzinfo=UTC)
NOT_BEFORE = "2026-07-30T00:00:00Z"
EXPIRES_AT = "2026-07-30T04:00:00Z"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_protected_read_rejects_mapped_drive_before_path_touch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touched: list[str] = []
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda _root: 4,
    )
    monkeypatch.setattr(
        egress_auth,
        "_assert_no_reparse_components",
        lambda _path: touched.append("lstat"),
    )
    monkeypatch.setattr(
        egress_auth,
        "_forbidden_path",
        lambda *_args, **_kwargs: touched.append("resolve") or False,
    )

    with pytest.raises(ConnectorEgressAuthorizationError) as exc_info:
        egress_auth._read_protected_bytes(
            r"Z:\proof\definition.json",
            expected_sha256="a" * 64,
            label="definition",
        )

    assert exc_info.value.code == "connector_egress_protected_path_invalid"
    assert touched == []


def _campaign_payload() -> dict[str, object]:
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


def _rules(connector_key: str) -> list[dict[str, object]]:
    if connector_key == "sciencebase_mcs":
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


def _grant_payload(
    connector_key: str,
    *,
    campaign_fingerprint: str,
    campaign_sha256: str,
    operator_mode: str,
) -> dict[str, object]:
    sciencebase = connector_key == "sciencebase_mcs"
    campaign = _campaign_payload()
    return {
        "schema_id": "project6.connector_egress_grant.v1",
        "grant_id": f"grant-{connector_key}-001",
        "connector_key": connector_key,
        "campaign_id": CAMPAIGN_ID,
        "campaign_fingerprint": campaign_fingerprint,
        "campaign_definition_sha256": campaign_sha256,
        "code_revision": CODE_REVISION,
        "arming_nonce": (
            "e571f24e-e703-4c4f-b9c1-0c542a14682c"
            if sciencebase
            else "2725d907-3277-4eb5-9052-ff76c666bfcb"
        ),
        "max_armings": 1,
        "issued_at": NOT_BEFORE,
        "expires_at": EXPIRES_AT,
        "operator_mode": operator_mode,
        "target": (
            campaign["sciencebase_target"] if sciencebase else campaign["nrc_target"]
        ),
        "request_rules": _rules(connector_key),
        "max_physical_requests": 3 if sciencebase else 2,
        "max_run_bytes": 140 * 1024 * 1024,
        "max_single_send_detection_allowance_bytes": SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
        "request_timeout_seconds": 30,
        "min_request_interval_ms": 250,
        "non_authorities": list(
            COMMON_GRANT_NON_AUTHORITIES if sciencebase else NRC_GRANT_NON_AUTHORITIES
        ),
    }


@dataclass
class AuthorityFixture:
    campaign_path: Path
    campaign_sha256: str
    campaign_fingerprint: str
    grant_paths: dict[str, Path]
    grant_sha256: dict[str, str]
    marker_paths: dict[str, Path]
    marker_models: dict[str, ConnectorGrantConsumptionMarkerV1]
    evidence_root: Path
    index_path: Path
    index_sha256: str


def _explicit_read_only_settings(
    fixture: AuthorityFixture,
    tmp_path: Path,
    *,
    index_path: Path | None = None,
    index_sha256: str | None = None,
) -> Settings:
    storage_dir = tmp_path / "explicit-storage"
    storage_dir.mkdir()
    database_path = tmp_path / "explicit.db"
    database_path.touch()
    return Settings(
        DB_INIT_MODE="none",
        DATABASE_URL=(
            f"sqlite:///{database_path.resolve().as_posix()}"
        ),
        STORAGE_DIR=str(storage_dir),
        CONNECTOR_CAMPAIGN_EVIDENCE_ROOT=fixture.evidence_root,
        CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH=(
            fixture.index_path if index_path is None else index_path
        ),
        CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256=(
            fixture.index_sha256
            if index_sha256 is None
            else index_sha256
        ),
    )


def _read_index(path: Path) -> ConnectorCampaignEvidenceIndexV1:
    return ConnectorCampaignEvidenceIndexV1.model_validate(
        egress_auth.strict_json_loads(path.read_bytes())
    )


def _write_index_head(
    fixture: AuthorityFixture,
    model: ConnectorCampaignEvidenceIndexV1,
    monkeypatch,
) -> tuple[Path, str]:
    raw_bytes = canonical_json_bytes(model)
    digest = _sha(raw_bytes)
    path = fixture.evidence_root / "indexes" / f"{digest}.json"
    path.write_bytes(raw_bytes)
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_path",
        path,
    )
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_sha256",
        digest,
    )
    return path, digest


def _append_valid_second_slice(
    fixture: AuthorityFixture,
    monkeypatch,
) -> tuple[Path, str]:
    predecessor = _read_index(fixture.index_path)
    campaign_payload: dict[str, Any] = _campaign_payload()
    campaign_payload["campaign_id"] = SECOND_CAMPAIGN_ID
    campaign = DualLiveCampaignDefinitionV1.model_validate(campaign_payload)
    campaign_bytes = canonical_json_bytes(campaign)
    campaign_sha256 = _sha(campaign_bytes)
    campaign_fingerprint = _sha(canonical_json_bytes(campaign))
    (
        fixture.evidence_root
        / "campaigns"
        / f"{campaign_sha256}.json"
    ).write_bytes(campaign_bytes)

    entries: list[dict[str, Any]] = []
    for connector_key, nonce in (
        ("sciencebase_mcs", "f6b5f031-0cc1-4387-a649-c0403fc89e77"),
        ("nrc_adams_aps", "80c734bc-8594-424a-aa32-b72561e94230"),
    ):
        grant_payload: dict[str, Any] = _grant_payload(
            connector_key,
            campaign_fingerprint=campaign_fingerprint,
            campaign_sha256=campaign_sha256,
            operator_mode="local_loopback",
        )
        grant_payload.update(
            {
                "grant_id": f"grant-{connector_key}-002",
                "campaign_id": SECOND_CAMPAIGN_ID,
                "arming_nonce": nonce,
            }
        )
        grant = ConnectorEgressGrantV1.model_validate(grant_payload)
        grant_bytes = canonical_json_bytes(grant)
        raw_grant_sha256 = _sha(grant_bytes)
        canonical_grant_fingerprint = _sha(canonical_json_bytes(grant))
        (
            fixture.evidence_root
            / "grants"
            / f"{raw_grant_sha256}.json"
        ).write_bytes(grant_bytes)
        marker = ConnectorGrantConsumptionMarkerV1.model_validate(
            {
                "schema_id": "project6.connector_grant_consumption.v1",
                "connector_key": connector_key,
                "campaign_id": SECOND_CAMPAIGN_ID,
                "campaign_fingerprint": campaign_fingerprint,
                "campaign_definition_sha256": campaign_sha256,
                "raw_grant_sha256": raw_grant_sha256,
                "canonical_grant_fingerprint": (
                    canonical_grant_fingerprint
                ),
                "arming_nonce": nonce,
                "connector_run_id": f"run-2-{connector_key}",
                "max_armings": 1,
            }
        )
        entries.append(
            {
                "campaign_id": SECOND_CAMPAIGN_ID,
                "campaign_fingerprint": campaign_fingerprint,
                "campaign_definition_sha256": campaign_sha256,
                "connector_key": connector_key,
                "code_revision": CODE_REVISION,
                "raw_grant_sha256": raw_grant_sha256,
                "canonical_grant_fingerprint": (
                    canonical_grant_fingerprint
                ),
                "grant_relative_path": (
                    f"grants/{raw_grant_sha256}.json"
                ),
                "consumption_marker_sha256": _sha(
                    canonical_json_bytes(marker)
                ),
                "consumption_marker_relative_path": (
                    f"consumed/{raw_grant_sha256}.json"
                ),
            }
        )

    successor = ConnectorCampaignEvidenceIndexV1.model_validate(
        {
            "schema_id": "project6.connector_campaign_evidence_index.v1",
            "revision": 2,
            "predecessor_index_sha256": fixture.index_sha256,
            "predecessor_index_relative_path": (
                f"indexes/{fixture.index_sha256}.json"
            ),
            "campaigns": [
                *(item.model_dump(mode="json") for item in predecessor.campaigns),
                {
                    "campaign_id": SECOND_CAMPAIGN_ID,
                    "campaign_fingerprint": campaign_fingerprint,
                    "code_revision": CODE_REVISION,
                    "raw_definition_sha256": campaign_sha256,
                    "definition_relative_path": (
                        f"campaigns/{campaign_sha256}.json"
                    ),
                },
            ],
            "entries": [
                *(item.model_dump(mode="json") for item in predecessor.entries),
                *entries,
            ],
            "log_captures": [
                *(
                    item.model_dump(mode="json")
                    for item in predecessor.log_captures
                ),
                {
                    "campaign_id": SECOND_CAMPAIGN_ID,
                    "campaign_fingerprint": campaign_fingerprint,
                    "campaign_definition_sha256": campaign_sha256,
                    "code_revision": CODE_REVISION,
                    "log_dir_relative_path": (
                        f"logs/{campaign_fingerprint}"
                    ),
                    "manifest_relative_path": (
                        f"logs/{campaign_fingerprint}/manifest.json"
                    ),
                    "seal_relative_path": (
                        f"log-seals/{campaign_fingerprint}.json"
                    ),
                    "expected_stream_files": (
                        "app.jsonl",
                        "http.jsonl",
                        "stdout.log",
                        "stderr.log",
                    ),
                },
            ],
        }
    )
    return _write_index_head(fixture, successor, monkeypatch)


def _build_authority(
    tmp_path: Path,
    monkeypatch,
    *,
    entry_path_override: str | None = None,
    operator_mode: str = "local_loopback",
) -> AuthorityFixture:
    authority_root = tmp_path / "authority"
    evidence_root = tmp_path / "evidence"
    for child in ("indexes", "campaigns", "grants", "consumed"):
        (evidence_root / child).mkdir(parents=True, exist_ok=True)
    authority_root.mkdir()

    campaign_model = DualLiveCampaignDefinitionV1.model_validate(_campaign_payload())
    campaign_bytes = canonical_json_bytes(campaign_model)
    campaign_sha256 = _sha(campaign_bytes)
    campaign_fingerprint = _sha(canonical_json_bytes(campaign_model))
    campaign_path = authority_root / "campaign.json"
    campaign_path.write_bytes(campaign_bytes)
    (evidence_root / "campaigns" / f"{campaign_sha256}.json").write_bytes(campaign_bytes)

    grant_paths: dict[str, Path] = {}
    grant_sha256: dict[str, str] = {}
    marker_paths: dict[str, Path] = {}
    marker_models: dict[str, ConnectorGrantConsumptionMarkerV1] = {}
    entries: list[dict[str, object]] = []
    for connector_key in ("sciencebase_mcs", "nrc_adams_aps"):
        grant_model = ConnectorEgressGrantV1.model_validate(
            _grant_payload(
                connector_key,
                campaign_fingerprint=campaign_fingerprint,
                campaign_sha256=campaign_sha256,
                operator_mode=operator_mode,
            )
        )
        grant_bytes = canonical_json_bytes(grant_model)
        raw_grant_sha256 = _sha(grant_bytes)
        canonical_grant_fingerprint = _sha(canonical_json_bytes(grant_model))
        grant_path = authority_root / f"{connector_key}.json"
        grant_path.write_bytes(grant_bytes)
        (evidence_root / "grants" / f"{raw_grant_sha256}.json").write_bytes(grant_bytes)

        marker_model = ConnectorGrantConsumptionMarkerV1(
            schema_id="project6.connector_grant_consumption.v1",
            connector_key=connector_key,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=campaign_fingerprint,
            campaign_definition_sha256=campaign_sha256,
            raw_grant_sha256=raw_grant_sha256,
            canonical_grant_fingerprint=canonical_grant_fingerprint,
            arming_nonce=grant_model.arming_nonce,
            connector_run_id=f"run-{connector_key}",
            max_armings=1,
        )
        marker_sha256 = _sha(canonical_json_bytes(marker_model))
        marker_path = evidence_root / "consumed" / f"{raw_grant_sha256}.json"
        grant_relative_path = (
            entry_path_override
            if connector_key == "sciencebase_mcs" and entry_path_override is not None
            else f"grants/{raw_grant_sha256}.json"
        )
        entries.append(
            {
                "campaign_id": CAMPAIGN_ID,
                "campaign_fingerprint": campaign_fingerprint,
                "campaign_definition_sha256": campaign_sha256,
                "connector_key": connector_key,
                "code_revision": CODE_REVISION,
                "raw_grant_sha256": raw_grant_sha256,
                "canonical_grant_fingerprint": canonical_grant_fingerprint,
                "grant_relative_path": grant_relative_path,
                "consumption_marker_sha256": marker_sha256,
                "consumption_marker_relative_path": (
                    f"consumed/{raw_grant_sha256}.json"
                ),
            }
        )
        grant_paths[connector_key] = grant_path
        grant_sha256[connector_key] = raw_grant_sha256
        marker_paths[connector_key] = marker_path
        marker_models[connector_key] = marker_model

    index_model = ConnectorCampaignEvidenceIndexV1.model_validate(
        {
            "schema_id": "project6.connector_campaign_evidence_index.v1",
            "revision": 1,
            "predecessor_index_sha256": None,
            "predecessor_index_relative_path": None,
            "campaigns": (
                {
                    "campaign_id": CAMPAIGN_ID,
                    "campaign_fingerprint": campaign_fingerprint,
                    "code_revision": CODE_REVISION,
                    "raw_definition_sha256": campaign_sha256,
                    "definition_relative_path": (
                        f"campaigns/{campaign_sha256}.json"
                    ),
                },
            ),
            "entries": tuple(entries),
            "log_captures": (
                {
                    "campaign_id": CAMPAIGN_ID,
                    "campaign_fingerprint": campaign_fingerprint,
                    "campaign_definition_sha256": campaign_sha256,
                    "code_revision": CODE_REVISION,
                    "log_dir_relative_path": (
                        f"logs/{campaign_fingerprint}"
                    ),
                    "manifest_relative_path": (
                        f"logs/{campaign_fingerprint}/manifest.json"
                    ),
                    "seal_relative_path": (
                        f"log-seals/{campaign_fingerprint}.json"
                    ),
                    "expected_stream_files": (
                        "app.jsonl",
                        "http.jsonl",
                        "stdout.log",
                        "stderr.log",
                    ),
                },
            ),
        }
    )
    index_bytes = canonical_json_bytes(index_model)
    index_sha256 = _sha(index_bytes)
    index_path = evidence_root / "indexes" / f"{index_sha256}.json"
    index_path.write_bytes(index_bytes)

    monkeypatch.setattr(settings, "connector_campaign_definition_path", campaign_path)
    monkeypatch.setattr(
        settings, "connector_campaign_definition_sha256", campaign_sha256
    )
    monkeypatch.setattr(
        settings, "connector_sciencebase_grant_path", grant_paths["sciencebase_mcs"]
    )
    monkeypatch.setattr(
        settings,
        "connector_sciencebase_grant_sha256",
        grant_sha256["sciencebase_mcs"],
    )
    monkeypatch.setattr(
        settings, "connector_nrc_aps_grant_path", grant_paths["nrc_adams_aps"]
    )
    monkeypatch.setattr(
        settings, "connector_nrc_aps_grant_sha256", grant_sha256["nrc_adams_aps"]
    )
    monkeypatch.setattr(settings, "connector_campaign_evidence_root", evidence_root)
    monkeypatch.setattr(settings, "connector_campaign_evidence_index_path", index_path)
    monkeypatch.setattr(
        settings, "connector_campaign_evidence_index_sha256", index_sha256
    )

    return AuthorityFixture(
        campaign_path=campaign_path,
        campaign_sha256=campaign_sha256,
        campaign_fingerprint=campaign_fingerprint,
        grant_paths=grant_paths,
        grant_sha256=grant_sha256,
        marker_paths=marker_paths,
        marker_models=marker_models,
        evidence_root=evidence_root,
        index_path=index_path,
        index_sha256=index_sha256,
    )


def _resolve(fixture: AuthorityFixture):
    campaign = resolve_current_dual_live_campaign_definition(
        expected_campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=fixture.campaign_fingerprint,
        code_revision=CODE_REVISION,
        now=NOW,
    )
    grant = resolve_current_connector_egress_grant(
        verified_campaign=campaign,
        connector_key="sciencebase_mcs",
        expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=fixture.campaign_fingerprint,
        code_revision=CODE_REVISION,
        now=NOW,
    )
    return campaign, grant


def _request(
    *,
    client_host: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/connectors/egress/arm",
            "headers": [
                (key.lower().encode("ascii"), value.encode("utf-8"))
                for key, value in (headers or {}).items()
            ],
            "client": (client_host, 44000),
            "server": ("127.0.0.1", 8000),
            "scheme": "http",
        }
    )


def _enable_local_runner_posture(monkeypatch) -> None:
    monkeypatch.setattr(settings, "deployment_mode", "local")
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(settings, "connector_live_egress_enabled", True)
    monkeypatch.setattr(
        settings,
        "connector_live_egress_exclusive_proof_mode",
        True,
    )


def _mock_current_user_sid_sha256(
    monkeypatch,
    value: str = "ab" * 32,
) -> None:
    from app.services import dual_live_windows

    monkeypatch.setattr(
        dual_live_windows,
        "current_user_sid_sha256",
        lambda: value,
    )


def _authority_json_digests(fixture: AuthorityFixture) -> dict[str, str]:
    return {
        str(path): _sha(path.read_bytes())
        for path in sorted(fixture.evidence_root.parent.rglob("*.json"))
    }


def test_current_resolvers_bind_definition_grant_and_index(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    campaign, grant = _resolve(fixture)

    assert campaign.model.campaign_id.hex == CAMPAIGN_ID.replace("-", "")
    assert campaign.raw_sha256 == fixture.campaign_sha256
    assert campaign.canonical_fingerprint == fixture.campaign_fingerprint
    assert campaign.introduction_index_revision == 1
    assert campaign.introduction_index_sha256 == fixture.index_sha256
    assert grant.model.connector_key == "sciencebase_mcs"
    assert grant.raw_sha256 == fixture.grant_sha256["sciencebase_mcs"]
    assert grant.verified_campaign is not campaign
    assert grant.verified_campaign.raw_sha256 == campaign.raw_sha256
    assert (
        grant.verified_campaign.introduction_index_sha256
        == campaign.introduction_index_sha256
    )
    assert grant.consumption_marker_path == fixture.marker_paths["sciencebase_mcs"]
    assert grant.consumption_marker_present is False


def test_grant_resolution_rejects_byte_identical_evidence_root_rebinding(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    campaign = resolve_current_dual_live_campaign_definition(
        expected_campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=fixture.campaign_fingerprint,
        code_revision=CODE_REVISION,
        now=NOW,
    )
    rebound = replace(
        campaign,
        evidence_root=tmp_path / "second-evidence-root",
    )
    monkeypatch.setattr(
        egress_auth,
        "resolve_current_dual_live_campaign_definition",
        lambda **_kwargs: rebound,
    )

    with pytest.raises(
        ConnectorEgressAuthorizationError,
        match="changed before connector grant resolution",
    ):
        resolve_current_connector_egress_grant(
            verified_campaign=campaign,
            connector_key="sciencebase_mcs",
            expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


def test_historical_resolver_requires_and_rehashes_consumption_marker(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    marker_path = fixture.marker_paths["sciencebase_mcs"]
    marker_path.write_bytes(
        canonical_json_bytes(fixture.marker_models["sciencebase_mcs"])
    )

    historical = resolve_historical_connector_grant_evidence(
        connector_key="sciencebase_mcs",
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=fixture.campaign_fingerprint,
        expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
    )
    assert isinstance(historical, VerifiedHistoricalGrantEvidence)
    assert historical.marker_model.connector_run_id == "run-sciencebase_mcs"

    marker_path.write_bytes(b"{}")
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_historical_connector_grant_evidence(
            connector_key="sciencebase_mcs",
            campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
        )


def test_explicit_settings_read_only_adapters_ignore_global_current_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    fixture.marker_paths["sciencebase_mcs"].write_bytes(
        canonical_json_bytes(fixture.marker_models["sciencebase_mcs"])
    )
    successor_path, successor_sha256 = _append_valid_second_slice(
        fixture,
        monkeypatch,
    )
    explicit = _explicit_read_only_settings(
        fixture,
        tmp_path,
        index_path=successor_path,
        index_sha256=successor_sha256,
    )

    with pytest.raises(ConnectorEgressAuthorizationError) as ancestor:
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )
    assert ancestor.value.code == "connector_egress_campaign_historical_only"

    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_root",
        tmp_path / "wrong-global-root",
    )
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_path",
        tmp_path / "wrong-global-index.json",
    )
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_sha256",
        "0" * 64,
    )
    monkeypatch.setattr(settings, "storage_dir", str(fixture.evidence_root))
    monkeypatch.setattr(
        egress_auth,
        "resolve_current_dual_live_campaign_definition",
        lambda **_kwargs: pytest.fail("current authority fallback"),
    )
    monkeypatch.setattr(
        egress_auth,
        "resolve_current_connector_egress_grant",
        lambda **_kwargs: pytest.fail("current grant fallback"),
    )

    chain = load_evidence_index_chain_read_only(explicit)
    historical = resolve_historical_connector_grant_evidence_read_only(
        explicit,
        connector_key="sciencebase_mcs",
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=fixture.campaign_fingerprint,
        expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
    )

    assert chain.head.revision == 2
    assert historical.index_chain.head.revision == 2
    assert historical.introduction_index_revision == 1
    assert historical.introduction_index_sha256 == fixture.index_sha256
    assert historical.marker_model == fixture.marker_models["sciencebase_mcs"]
    assert tuple(
        inspect.signature(load_evidence_index_chain_read_only).parameters
    ) == ("settings",)
    assert tuple(
        inspect.signature(
            resolve_historical_connector_grant_evidence_read_only
        ).parameters
    ) == (
        "settings",
        "connector_key",
        "campaign_id",
        "expected_campaign_fingerprint",
        "expected_grant_sha256",
    )

    orphan = fixture.evidence_root / "indexes" / f"{'0' * 64}.json"
    orphan.write_bytes(successor_path.read_bytes())
    with pytest.raises(
        ConnectorEgressAuthorizationError,
        match="raw-byte|linear chain|digest filename",
    ):
        load_evidence_index_chain_read_only(explicit)


@pytest.mark.parametrize("surface", ("index", "archive"))
def test_read_only_traversal_frozen_ceilings_fail_at_max_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    fixture.marker_paths["sciencebase_mcs"].write_bytes(
        canonical_json_bytes(fixture.marker_models["sciencebase_mcs"])
    )
    successor_path, successor_sha256 = _append_valid_second_slice(
        fixture,
        monkeypatch,
    )
    explicit = _explicit_read_only_settings(
        fixture,
        tmp_path,
        index_path=successor_path,
        index_sha256=successor_sha256,
    )
    assert egress_auth.MAX_EVIDENCE_INDEX_REVISIONS == 128
    assert egress_auth.MAX_EVIDENCE_CAMPAIGN_ARCHIVES == 128
    assert egress_auth.MAX_EVIDENCE_GRANT_ARCHIVES == 256
    assert egress_auth.MAX_EVIDENCE_LOG_CAPTURE_REFS == 128

    if surface == "index":
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_INDEX_REVISIONS", 2)
        assert load_evidence_index_chain_read_only(explicit).head.revision == 2
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_INDEX_REVISIONS", 1)
        expected_code = "connector_egress_index_revision_limit_exceeded"
    else:
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_INDEX_REVISIONS", 2)
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_CAMPAIGN_ARCHIVES", 2)
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_GRANT_ARCHIVES", 4)
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_LOG_CAPTURE_REFS", 2)
        verified = resolve_historical_connector_grant_evidence_read_only(
            explicit,
            connector_key="sciencebase_mcs",
            campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
        )
        assert verified.index_chain.head.revision == 2
        monkeypatch.setattr(egress_auth, "MAX_EVIDENCE_CAMPAIGN_ARCHIVES", 1)
        expected_code = "connector_egress_archive_limit_exceeded"

    with pytest.raises(ConnectorEgressAuthorizationError) as excinfo:
        if surface == "index":
            load_evidence_index_chain_read_only(explicit)
        else:
            resolve_historical_connector_grant_evidence_read_only(
                explicit,
                connector_key="sciencebase_mcs",
                campaign_id=CAMPAIGN_ID,
                expected_campaign_fingerprint=fixture.campaign_fingerprint,
                expected_grant_sha256=fixture.grant_sha256[
                    "sciencebase_mcs"
                ],
            )
    assert excinfo.value.code == expected_code


def test_historical_read_only_adapter_finishes_with_targeted_rereads_then_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    fixture.marker_paths["sciencebase_mcs"].write_bytes(
        canonical_json_bytes(fixture.marker_models["sciencebase_mcs"])
    )
    explicit = _explicit_read_only_settings(fixture, tmp_path)
    calls: list[str] = []
    originals: dict[str, Callable[..., Any]] = {
        "definition": egress_auth._read_archived_definition,
        "grant": egress_auth._read_archived_grant,
        "marker": egress_auth._read_marker_if_present,
        "index": egress_auth._assert_evidence_index_chain_unchanged,
    }

    def wrap(name: str) -> Callable[..., Any]:
        def tracked(*args: Any, **kwargs: Any) -> Any:
            calls.append(name)
            return originals[name](*args, **kwargs)

        return tracked

    monkeypatch.setattr(
        egress_auth,
        "_read_archived_definition",
        wrap("definition"),
    )
    monkeypatch.setattr(egress_auth, "_read_archived_grant", wrap("grant"))
    monkeypatch.setattr(egress_auth, "_read_marker_if_present", wrap("marker"))
    monkeypatch.setattr(
        egress_auth,
        "_assert_evidence_index_chain_unchanged",
        wrap("index"),
    )

    verified = resolve_historical_connector_grant_evidence_read_only(
        explicit,
        connector_key="sciencebase_mcs",
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=fixture.campaign_fingerprint,
        expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
    )

    assert verified.marker_model == fixture.marker_models["sciencebase_mcs"]
    assert calls[-4:] == ["definition", "grant", "marker", "index"]


def test_changed_or_duplicate_campaign_bytes_fail_closed(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    fixture.campaign_path.write_bytes(
        (
            '{"schema_id":"project6.dual_live_campaign_definition.v1",'
            '"campaign_id":"one","campaign_id":"two"}'
        ).encode("utf-8")
    )
    monkeypatch.setattr(
        settings,
        "connector_campaign_definition_sha256",
        _sha(fixture.campaign_path.read_bytes()),
    )
    with pytest.raises(ConnectorEgressAuthorizationError, match="duplicate"):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


@pytest.mark.parametrize(
    "failure",
    ["missing", "oversized", "digest_mismatch"],
)
def test_protected_campaign_input_failures_are_closed(
    tmp_path, monkeypatch, failure: str
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    if failure == "missing":
        monkeypatch.setattr(
            settings,
            "connector_campaign_definition_path",
            tmp_path / "missing-campaign.json",
        )
    elif failure == "oversized":
        oversized = tmp_path / "oversized-campaign.json"
        oversized.write_bytes(b"x" * (64 * 1024 + 1))
        monkeypatch.setattr(
            settings,
            "connector_campaign_definition_path",
            oversized,
        )
        monkeypatch.setattr(
            settings,
            "connector_campaign_definition_sha256",
            _sha(oversized.read_bytes()),
        )
    else:
        monkeypatch.setattr(
            settings,
            "connector_campaign_definition_sha256",
            "f" * 64,
        )

    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


@pytest.mark.parametrize(
    "failure",
    ["missing", "oversized", "digest_mismatch"],
)
def test_protected_grant_input_failures_are_closed(
    tmp_path, monkeypatch, failure: str
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    campaign = resolve_current_dual_live_campaign_definition(
        expected_campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=fixture.campaign_fingerprint,
        code_revision=CODE_REVISION,
        now=NOW,
    )
    if failure == "missing":
        monkeypatch.setattr(
            settings,
            "connector_sciencebase_grant_path",
            tmp_path / "missing-grant.json",
        )
    elif failure == "oversized":
        oversized = tmp_path / "oversized-grant.json"
        oversized.write_bytes(b"x" * (64 * 1024 + 1))
        monkeypatch.setattr(
            settings,
            "connector_sciencebase_grant_path",
            oversized,
        )
        monkeypatch.setattr(
            settings,
            "connector_sciencebase_grant_sha256",
            _sha(oversized.read_bytes()),
        )
    else:
        monkeypatch.setattr(
            settings,
            "connector_sciencebase_grant_sha256",
            "f" * 64,
        )

    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_connector_egress_grant(
            verified_campaign=campaign,
            connector_key="sciencebase_mcs",
            expected_grant_sha256=fixture.grant_sha256["sciencebase_mcs"],
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


def test_protected_symlink_and_mocked_reparse_paths_fail_closed(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    link = tmp_path / "campaign-link.json"
    try:
        link.symlink_to(fixture.campaign_path)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    monkeypatch.setattr(
        settings,
        "connector_campaign_definition_path",
        link,
    )
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )

    monkeypatch.setattr(
        egress_auth.os,
        "lstat",
        lambda _path: SimpleNamespace(
            st_mode=0,
            st_file_attributes=0x400,
        ),
    )
    with pytest.raises(ConnectorEgressAuthorizationError):
        egress_auth._assert_no_reparse_components(fixture.campaign_path)


def test_configured_index_head_symlink_alias_fails_closed(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    alias = tmp_path / "index-head-link.json"
    try:
        alias.symlink_to(fixture.index_path)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_path",
        alias,
    )
    with pytest.raises(ConnectorEgressAuthorizationError):
        egress_auth._load_evidence_index_chain()


@pytest.mark.skipif(os.name != "nt", reason="NTFS ADS syntax is Windows-only")
def test_protected_ads_path_fails_closed(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    monkeypatch.setattr(
        settings,
        "connector_campaign_definition_path",
        Path(f"{fixture.campaign_path}:hidden"),
    )
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


def test_index_rejects_orphan_content_addressed_object(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    orphan = fixture.evidence_root / "indexes" / f"{'f' * 64}.json"
    orphan.write_bytes(fixture.index_path.read_bytes())
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


def test_valid_revision_two_chain_is_accepted(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    _, head_sha256 = _append_valid_second_slice(fixture, monkeypatch)

    chain = egress_auth._load_evidence_index_chain()

    assert tuple(item.model.revision for item in chain.revisions) == (1, 2)
    assert chain.head_raw_sha256 == head_sha256


def test_configured_rollback_head_is_rejected(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    _append_valid_second_slice(fixture, monkeypatch)
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_path",
        fixture.index_path,
    )
    monkeypatch.setattr(
        settings,
        "connector_campaign_evidence_index_sha256",
        fixture.index_sha256,
    )

    with pytest.raises(
        ConnectorEgressAuthorizationError,
        match="unique maximal revision",
    ):
        egress_auth._load_evidence_index_chain()


@pytest.mark.parametrize(
    ("revision", "predecessor_sha256", "expected_message"),
    [
        (3, None, "gap-free"),
        (2, "f" * 64, "predecessor object is missing"),
    ],
)
def test_revision_gap_and_wrong_predecessor_fail_closed(
    tmp_path,
    monkeypatch,
    revision: int,
    predecessor_sha256: str | None,
    expected_message: str,
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    predecessor = _read_index(fixture.index_path)
    predecessor_digest = predecessor_sha256 or fixture.index_sha256
    successor = ConnectorCampaignEvidenceIndexV1.model_validate(
        {
            **predecessor.model_dump(mode="json"),
            "revision": revision,
            "predecessor_index_sha256": predecessor_digest,
            "predecessor_index_relative_path": (
                f"indexes/{predecessor_digest}.json"
            ),
        }
    )
    _write_index_head(fixture, successor, monkeypatch)

    with pytest.raises(
        ConnectorEgressAuthorizationError,
        match=expected_message,
    ):
        egress_auth._load_evidence_index_chain()


def test_forked_chain_fails_closed(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    predecessor = _read_index(fixture.index_path)
    common = {
        **predecessor.model_dump(mode="json"),
        "predecessor_index_sha256": fixture.index_sha256,
        "predecessor_index_relative_path": (
            f"indexes/{fixture.index_sha256}.json"
        ),
    }
    branch = ConnectorCampaignEvidenceIndexV1.model_validate(
        {**common, "revision": 2}
    )
    _write_index_head(fixture, branch, monkeypatch)
    fork = ConnectorCampaignEvidenceIndexV1.model_validate(
        {**common, "revision": 3}
    )
    _write_index_head(fixture, fork, monkeypatch)

    with pytest.raises(
        ConnectorEgressAuthorizationError,
        match="linear chain",
    ):
        egress_auth._load_evidence_index_chain()


@pytest.mark.parametrize(
    "mutation",
    ["dropped_prior_refs", "partial_slice", "missing_capture", "duplicate_capture"],
)
def test_non_append_only_or_incomplete_successor_fails_closed(
    tmp_path,
    monkeypatch,
    mutation: str,
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    predecessor = _read_index(fixture.index_path)
    payload: dict[str, Any] = {
        **predecessor.model_dump(mode="json"),
        "revision": 2,
        "predecessor_index_sha256": fixture.index_sha256,
        "predecessor_index_relative_path": (
            f"indexes/{fixture.index_sha256}.json"
        ),
    }
    if mutation == "partial_slice":
        payload["campaigns"] = [
            *payload["campaigns"],
            {
                **payload["campaigns"][0],
                "campaign_id": SECOND_CAMPAIGN_ID,
                "campaign_fingerprint": "9" * 64,
            },
        ]
    elif mutation == "missing_capture":
        payload["log_captures"] = []
    elif mutation == "duplicate_capture":
        payload["log_captures"] = [
            *payload["log_captures"],
            payload["log_captures"][0],
        ]
    successor = ConnectorCampaignEvidenceIndexV1.model_validate(payload)
    _write_index_head(fixture, successor, monkeypatch)

    with pytest.raises(ConnectorEgressAuthorizationError):
        egress_auth._load_evidence_index_chain()


def test_non_content_addressed_index_filename_fails_closed(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    invalid_name = fixture.evidence_root / "indexes" / "not-a-digest.json"
    invalid_name.write_bytes(fixture.index_path.read_bytes())
    with pytest.raises(ConnectorEgressAuthorizationError):
        egress_auth._load_evidence_index_chain()


def test_case_variant_index_reference_path_fails_closed(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    predecessor = _read_index(fixture.index_path)
    payload = predecessor.model_dump(mode="json")
    payload["campaigns"][0]["definition_relative_path"] = (
        payload["campaigns"][0]["definition_relative_path"].replace(
            "campaigns/",
            "Campaigns/",
        )
    )
    case_variant = ConnectorCampaignEvidenceIndexV1.model_validate(payload)
    _write_index_head(fixture, case_variant, monkeypatch)
    with pytest.raises(ConnectorEgressAuthorizationError):
        egress_auth._load_evidence_index_chain()


def test_index_membership_change_during_resolution_fails_closed(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    original = egress_auth._read_archived_definition
    orphan = fixture.evidence_root / "indexes" / f"{'f' * 64}.json"
    injected = False

    def _inject_orphan(*args, **kwargs):
        nonlocal injected
        result = original(*args, **kwargs)
        if not injected:
            orphan.write_bytes(fixture.index_path.read_bytes())
            injected = True
        return result

    monkeypatch.setattr(
        egress_auth,
        "_read_archived_definition",
        _inject_orphan,
    )
    with pytest.raises(
        ConnectorEgressAuthorizationError,
        match="membership changed",
    ):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


def test_index_rejects_traversing_grant_reference(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(
        tmp_path,
        monkeypatch,
        entry_path_override="../grants/escape.json",
    )
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=NOW,
        )


def test_wrong_revision_and_expiry_are_half_open_failures(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision="d" * 40,
            now=NOW,
        )
    with pytest.raises(ConnectorEgressAuthorizationError):
        resolve_current_dual_live_campaign_definition(
            expected_campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=fixture.campaign_fingerprint,
            code_revision=CODE_REVISION,
            now=datetime(2026, 7, 30, 4, 0, tzinfo=UTC),
        )


def test_local_caller_posture_is_flag_and_loopback_gated(tmp_path, monkeypatch) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    _, grant = _resolve(fixture)
    monkeypatch.setattr(settings, "deployment_mode", "local")
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")
    monkeypatch.setattr(settings, "connector_live_egress_enabled", False)
    monkeypatch.setattr(settings, "connector_live_egress_exclusive_proof_mode", True)

    with pytest.raises(ConnectorEgressAuthorizationError):
        authorize_connector_egress_owner(_request(), verified_grant=grant, access="write")

    monkeypatch.setattr(settings, "connector_live_egress_enabled", True)
    receipt = authorize_connector_egress_owner(
        _request(), verified_grant=grant, access="write"
    )
    assert receipt.operator_ref_hash
    assert receipt.workspace_ref_hash
    assert receipt.role is None
    assert "127.0.0.1" not in canonical_json_bytes(receipt).decode("utf-8")

    with pytest.raises(ConnectorEgressAuthorizationError):
        authorize_connector_egress_owner(
            _request(client_host="192.0.2.10"),
            verified_grant=grant,
            access="write",
        )
    with pytest.raises(ConnectorEgressAuthorizationError):
        authorize_connector_egress_owner(
            _request(headers={"X-Forwarded-User": "raw-identity"}),
            verified_grant=grant,
            access="write",
        )


def test_proxy_identity_presence_is_denied_and_owner_role_is_required(
    tmp_path, monkeypatch
) -> None:
    fixture = _build_authority(
        tmp_path,
        monkeypatch,
        operator_mode="proxy_owner",
    )
    _, grant = _resolve(fixture)
    monkeypatch.setattr(settings, "connector_live_egress_enabled", True)
    monkeypatch.setattr(settings, "connector_live_egress_exclusive_proof_mode", True)
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "X-Forwarded-User")
    monkeypatch.setattr(settings, "proxy_groups_header", "X-Forwarded-Groups")
    monkeypatch.setattr(settings, "proxy_roles_header", "X-Forwarded-Roles")
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    headers = {
        "X-Forwarded-User": "operator@example.invalid",
        "X-Forwarded-Groups": "workspace-1",
        "X-Forwarded-Roles": "owner",
    }

    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")
    with pytest.raises(ConnectorEgressAuthorizationError):
        authorize_connector_egress_owner(
            _request(headers=headers), verified_grant=grant, access="write"
        )

    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
    receipt = authorize_connector_egress_owner(
        _request(headers=headers), verified_grant=grant, access="write"
    )
    assert receipt.role == "owner"
    assert "operator@example.invalid" not in canonical_json_bytes(receipt).decode("utf-8")


def test_local_runner_owner_receipt_is_os_bound_and_arming_valid(
    tmp_path,
    monkeypatch,
) -> None:
    from app.services import connector_egress_arming

    fixture = _build_authority(tmp_path, monkeypatch)
    _, grant = _resolve(fixture)
    _enable_local_runner_posture(monkeypatch)
    sid_sha256 = "ab" * 32
    _mock_current_user_sid_sha256(monkeypatch, sid_sha256)

    authorize = egress_auth.authorize_connector_egress_local_runner
    parameters = tuple(inspect.signature(authorize).parameters.values())
    assert tuple(parameter.name for parameter in parameters) == (
        "verified_grant",
        "access",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in parameters
    )

    receipt = authorize(verified_grant=grant, access="write")
    campaign = grant.verified_campaign
    assert receipt.model_dump(
        include={
            "connector_key",
            "campaign_id",
            "campaign_fingerprint",
            "campaign_definition_sha256",
            "grant_sha256",
            "canonical_grant_fingerprint",
            "introduction_index_revision",
            "introduction_index_sha256",
            "access",
        },
        mode="json",
    ) == {
        "connector_key": grant.model.connector_key,
        "campaign_id": str(campaign.model.campaign_id),
        "campaign_fingerprint": campaign.canonical_fingerprint,
        "campaign_definition_sha256": campaign.raw_sha256,
        "grant_sha256": grant.raw_sha256,
        "canonical_grant_fingerprint": grant.canonical_fingerprint,
        "introduction_index_revision": campaign.introduction_index_revision,
        "introduction_index_sha256": campaign.introduction_index_sha256,
        "access": "write",
    }
    assert receipt.auth_owner_mode == (
        "AUTH_OWNER_none_single_operator_dev_profile"
    )
    assert receipt.authorization_mode == "identity_presence"
    assert receipt.role is None
    assert receipt.operator_ref_hash != sid_sha256
    assert receipt.operator_ref_hash != receipt.workspace_ref_hash

    encoded = canonical_json_bytes(receipt).decode("utf-8")
    assert sid_sha256 not in encoded
    assert str(egress_auth.BACKEND_ROOT.parent.resolve()) not in encoded
    assert connector_egress_arming._validated_authorization_receipt(
        receipt.model_dump(mode="json"),
        verified_grant=grant,
    ) == receipt

    _mock_current_user_sid_sha256(monkeypatch, "cd" * 32)
    rebound = authorize(verified_grant=grant, access="write")
    assert rebound.operator_ref_hash != receipt.operator_ref_hash
    assert rebound.workspace_ref_hash == receipt.workspace_ref_hash


@pytest.mark.parametrize(
    (
        "access",
        "setting_name",
        "setting_value",
        "expected_code",
    ),
    (
        (
            "read",
            None,
            None,
            "connector_egress_access_class_not_admitted",
        ),
        (
            "write",
            "connector_live_egress_enabled",
            False,
            "sciencebase_mcs_egress_default_off",
        ),
        (
            "write",
            "connector_live_egress_exclusive_proof_mode",
            False,
            "sciencebase_mcs_egress_exclusive_mode_required",
        ),
        (
            "write",
            "deployment_mode",
            "production",
            "sciencebase_mcs_egress_local_runner_posture_denied",
        ),
        (
            "write",
            "auth_owner",
            "proxy",
            "sciencebase_mcs_egress_local_runner_posture_denied",
        ),
        (
            "write",
            "trusted_proxy_mode",
            True,
            "sciencebase_mcs_egress_local_runner_posture_denied",
        ),
    ),
)
def test_local_runner_owner_refuses_unadmitted_posture_without_mutation(
    tmp_path,
    monkeypatch,
    access,
    setting_name,
    setting_value,
    expected_code,
) -> None:
    from app.services import dual_live_windows

    fixture = _build_authority(tmp_path, monkeypatch)
    _, grant = _resolve(fixture)
    _enable_local_runner_posture(monkeypatch)
    sid_calls: list[bool] = []
    monkeypatch.setattr(
        dual_live_windows,
        "current_user_sid_sha256",
        lambda: sid_calls.append(True) or "ab" * 32,
    )
    if setting_name is not None:
        monkeypatch.setattr(settings, setting_name, setting_value)
    before = _authority_json_digests(fixture)

    with pytest.raises(ConnectorEgressAuthorizationError) as exc:
        egress_auth.authorize_connector_egress_local_runner(
            verified_grant=grant,
            access=access,
        )

    assert exc.value.code == expected_code
    assert sid_calls == []
    assert _authority_json_digests(fixture) == before


def test_local_runner_owner_refuses_proxy_grant_and_changed_integrity(
    tmp_path,
    monkeypatch,
) -> None:
    proxy_fixture = _build_authority(
        tmp_path / "proxy",
        monkeypatch,
        operator_mode="proxy_owner",
    )
    _, proxy_grant = _resolve(proxy_fixture)
    _enable_local_runner_posture(monkeypatch)
    _mock_current_user_sid_sha256(monkeypatch)
    before = _authority_json_digests(proxy_fixture)

    with pytest.raises(ConnectorEgressAuthorizationError) as exc:
        egress_auth.authorize_connector_egress_local_runner(
            verified_grant=proxy_grant,
            access="write",
        )

    assert exc.value.code == (
        "sciencebase_mcs_egress_local_runner_posture_denied"
    )
    assert _authority_json_digests(proxy_fixture) == before

    local_fixture = _build_authority(
        tmp_path / "local",
        monkeypatch,
    )
    _, local_grant = _resolve(local_fixture)
    changed_grant = replace(local_grant, raw_sha256="0" * 64)
    before = _authority_json_digests(local_fixture)

    with pytest.raises(ConnectorEgressAuthorizationError) as exc:
        egress_auth.authorize_connector_egress_local_runner(
            verified_grant=changed_grant,
            access="write",
        )

    assert exc.value.code == "sciencebase_mcs_egress_verified_grant_changed"
    assert _authority_json_digests(local_fixture) == before


def test_local_runner_owner_refuses_invalid_sid_digest(
    tmp_path,
    monkeypatch,
) -> None:
    fixture = _build_authority(tmp_path, monkeypatch)
    _, grant = _resolve(fixture)
    _enable_local_runner_posture(monkeypatch)
    _mock_current_user_sid_sha256(monkeypatch, "not-a-sha256")
    before = _authority_json_digests(fixture)

    with pytest.raises(ConnectorEgressAuthorizationError) as exc:
        egress_auth.authorize_connector_egress_local_runner(
            verified_grant=grant,
            access="write",
        )

    assert exc.value.code == (
        "sciencebase_mcs_egress_local_runner_identity_invalid"
    )
    assert _authority_json_digests(fixture) == before
