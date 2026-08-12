"""Default-off ScienceBase producer with no ambient effect capability."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from backend.app.services.connector_egress_contract import (
    EffectPort,
    EffectResult,
    PhysicalRequestPlan,
    RequestLimits,
)


SCIENCEBASE_RESPONSE_CAP_BYTES = 64 * 1024 * 1024
_EMPTY_BODY_SHA256 = "sha256:" + hashlib.sha256(b"").hexdigest()
_SEARCH_ROOT = "https://www.sciencebase.gov/catalog"
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_SCIENCEBASE_HOSTS = {"sciencebase.gov", "www.sciencebase.gov"}
_UNRESERVED = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


class ProducerHold(ValueError):
    pass


@dataclass(frozen=True)
class ScienceBaseInput:
    query: str
    expected_item_id: str
    expected_file_name: str
    envelope_digest: str
    campaign_id: str
    canonical_root: str
    connector_run_id: str
    authorization_digest: str
    grant_digest: str
    max_total_bytes: int
    limits: RequestLimits
    max_redirect_hops: int = 0
    connector_run_target_id: str | None = None


@dataclass(frozen=True)
class ScienceBaseOutput:
    item_id: str
    file_name: str
    content: bytes
    sha256: str
    request_count: int
    total_response_bytes: int


@dataclass
class _AcquisitionState:
    next_ordinal: int = 1
    response_bytes: int = 0


def _quote_component(value: str) -> str:
    encoded: list[str] = []
    for byte in value.encode("utf-8"):
        encoded.append(chr(byte) if byte in _UNRESERVED else f"%{byte:02X}")
    return "".join(encoded)


def _safe_sciencebase_destination(value: object) -> str:
    if not isinstance(value, str):
        raise ProducerHold("sciencebase_destination_invalid")
    if (
        not value
        or value != value.strip()
        or not value.startswith("https://")
        or "#" in value
        or "\\" in value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise ProducerHold("sciencebase_destination_invalid")
    remainder = value[len("https://") :]
    authority = remainder.split("/", 1)[0].split("?", 1)[0]
    if "@" in authority:
        raise ProducerHold("sciencebase_destination_invalid")
    host, separator, port = authority.partition(":")
    if host not in _SCIENCEBASE_HOSTS or (separator and port != "443"):
        raise ProducerHold("sciencebase_destination_invalid")
    return value


def _strict_json_object(body: bytes, *, stage: str) -> dict[str, Any]:
    def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ProducerHold(f"sciencebase_{stage}_json_invalid")
            value[key] = item
        return value

    try:
        parsed = json.loads(body.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProducerHold(f"sciencebase_{stage}_json_invalid") from exc
    if not isinstance(parsed, dict):
        raise ProducerHold(f"sciencebase_{stage}_shape_invalid")
    return parsed


def _validate_input(request: ScienceBaseInput) -> None:
    text_fields = (
        request.query,
        request.expected_item_id,
        request.expected_file_name,
        request.envelope_digest,
        request.campaign_id,
        request.canonical_root,
        request.connector_run_id,
        request.authorization_digest,
        request.grant_digest,
    )
    if any(not isinstance(value, str) or not value or value != value.strip() for value in text_fields):
        raise ProducerHold("sciencebase_input_invalid")
    if (
        not isinstance(request.max_total_bytes, int)
        or request.max_total_bytes <= 0
        or not isinstance(request.max_redirect_hops, int)
        or not 0 <= request.max_redirect_hops <= 4
    ):
        raise ProducerHold("sciencebase_input_invalid")
    if request.limits.max_response_bytes > SCIENCEBASE_RESPONSE_CAP_BYTES:
        raise ProducerHold("sciencebase_response_limit_invalid")


class ScienceBaseProducer:
    def __init__(self, effect_port: EffectPort) -> None:
        self._effect_port = effect_port

    def acquire_exact_file(self, request: ScienceBaseInput) -> ScienceBaseOutput:
        _validate_input(request)
        state = _AcquisitionState()
        search_url = f"{_SEARCH_ROOT}/items?q={_quote_component(request.query)}&format=json"
        search = self._execute_stage(request, state, "sciencebase_search", search_url)
        search_payload = _strict_json_object(search.body, stage="search")
        items = search_payload.get("items")
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ProducerHold("sciencebase_search_shape_invalid")
        exact_items = [item for item in items if item.get("id") == request.expected_item_id]
        if len(exact_items) != 1:
            raise ProducerHold("sciencebase_exact_item_not_unique")

        item_url = f"{_SEARCH_ROOT}/item/{_quote_component(request.expected_item_id)}?format=json"
        hydration = self._execute_stage(request, state, "sciencebase_hydrate", item_url)
        item = _strict_json_object(hydration.body, stage="hydration")
        if item.get("id") != request.expected_item_id:
            raise ProducerHold("sciencebase_hydrated_item_mismatch")
        files = item.get("files")
        if not isinstance(files, list) or any(not isinstance(entry, dict) for entry in files):
            raise ProducerHold("sciencebase_hydration_shape_invalid")
        exact_files = [entry for entry in files if entry.get("name") == request.expected_file_name]
        if len(exact_files) != 1:
            raise ProducerHold("sciencebase_exact_file_not_unique")
        download_uri = self._exact_download_uri(exact_files[0])

        artifact = self._execute_stage(request, state, "sciencebase_download", download_uri)
        return ScienceBaseOutput(
            item_id=request.expected_item_id,
            file_name=request.expected_file_name,
            content=artifact.body,
            sha256=hashlib.sha256(artifact.body).hexdigest(),
            request_count=state.next_ordinal - 1,
            total_response_bytes=state.response_bytes,
        )

    @staticmethod
    def _exact_download_uri(entry: dict[str, Any]) -> str:
        raw_uri = entry.get("downloadUri")
        alias = entry.get("url")
        if (
            not isinstance(raw_uri, str)
            or not raw_uri
            or ("url" in entry and (not isinstance(alias, str) or alias != raw_uri))
        ):
            raise ProducerHold("sciencebase_exact_file_locator_invalid")
        try:
            return _safe_sciencebase_destination(raw_uri)
        except ProducerHold as exc:
            raise ProducerHold("sciencebase_exact_file_locator_invalid") from exc

    def _execute_stage(
        self,
        request: ScienceBaseInput,
        state: _AcquisitionState,
        stage: str,
        destination: str,
    ) -> EffectResult:
        current = _safe_sciencebase_destination(destination)
        redirect_count = 0
        while True:
            physical_stage = stage if redirect_count == 0 else f"{stage}_redirect"
            plan = self._plan(request, state.next_ordinal, physical_stage, current)
            state.next_ordinal += 1
            try:
                result = self._effect_port.execute(plan)
            except Exception:
                raise ProducerHold("sciencebase_effect_hold") from None
            self._validate_result(result, plan, request, state)
            if result.status_code not in _REDIRECT_STATUSES:
                if result.status_code != 200 or result.redirect_location is not None:
                    raise ProducerHold("sciencebase_status_rejected")
                return result
            if result.body:
                raise ProducerHold("sciencebase_redirect_body_rejected")
            if redirect_count >= request.max_redirect_hops:
                raise ProducerHold("sciencebase_redirect_limit_exceeded")
            current = _safe_sciencebase_destination(result.redirect_location)
            redirect_count += 1

    @staticmethod
    def _plan(
        request: ScienceBaseInput,
        ordinal: int,
        stage: str,
        destination: str,
    ) -> PhysicalRequestPlan:
        return PhysicalRequestPlan(
            envelope_digest=request.envelope_digest,
            campaign_id=request.campaign_id,
            canonical_root=request.canonical_root,
            connector_run_id=request.connector_run_id,
            target_id=request.connector_run_target_id or request.expected_item_id,
            request_ordinal=ordinal,
            stage=stage,
            method="GET",
            canonical_destination=destination,
            header_names=(),
            header_value_sha256s=(),
            body_sha256=_EMPTY_BODY_SHA256,
            limits=request.limits,
            authorization_digest=request.authorization_digest,
            grant_digest=request.grant_digest,
        )

    @staticmethod
    def _validate_result(
        result: EffectResult,
        plan: PhysicalRequestPlan,
        request: ScienceBaseInput,
        state: _AcquisitionState,
    ) -> None:
        if (
            not isinstance(result.status_code, int)
            or not isinstance(result.body, bytes)
            or not isinstance(result.response_header_names, tuple)
            or not isinstance(result.reservation_event_id, str)
            or not result.reservation_event_id
            or result.plan_digest != plan.plan_digest
        ):
            raise ProducerHold("sciencebase_effect_result_invalid")
        if len(result.body) > request.limits.max_response_bytes:
            raise ProducerHold("sciencebase_response_limit_exceeded")
        state.response_bytes += len(result.body)
        if state.response_bytes > request.max_total_bytes:
            raise ProducerHold("sciencebase_run_limit_exceeded")
