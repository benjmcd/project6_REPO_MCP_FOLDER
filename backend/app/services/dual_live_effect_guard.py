"""Secret-free, fail-closed primitives for the dual-live effect boundary.

This module is deliberately usable on non-Windows hosts.  It owns the small
wire contract shared by the broker and the AppContainer worker, but it owns no
authority and performs no ambient discovery.  Frames are bounded canonical
JSON so diagnostics can compare bytes without ever carrying credential values.
"""

from __future__ import annotations

import json
import base64
import hashlib
import re
import struct
import threading
from dataclasses import dataclass
from typing import Any, BinaryIO, Callable, Mapping, Protocol

from app.services.connector_egress_contract import (
    ContractHold,
    EffectResult,
    PhysicalRequestPlan,
    RequestLimits,
    physical_request_plan_from_document,
)
from app.services.dual_live_sciencebase_producer import (
    ScienceBaseInput,
    ScienceBaseOutput,
    ScienceBaseProducer,
)


MAX_FRAME_BYTES = 64 * 1024
_CODE = re.compile(r"[a-z][a-z0-9_]{1,63}\Z")
_DIGEST = re.compile(r"(?:sha256:)?[0-9a-f]{64}\Z")
_REFERENCE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
_HEADER_NAME = re.compile(r"[a-z0-9-]{1,64}\Z")
_BODY_CHUNK_BYTES = 32 * 1024
_ALLOWED_KEYS = frozenset(
    {
        "type", "code", "ok", "plan", "schema", "envelope_digest", "campaign_id",
        "canonical_root", "connector_run_id", "target_id", "request_ordinal", "stage",
        "method", "canonical_destination", "header_names", "header_value_sha256s",
        "body_sha256", "limits", "timeout_seconds", "max_response_bytes", "max_redirects",
        "authorization_digest", "grant_digest", "reservation_event_id", "plan_digest",
        "status_code", "response_header_names", "redirect_location", "body_size",
        "body_digest", "index", "data_b64", "request", "query", "expected_item_id",
        "expected_file_name", "max_total_bytes", "max_redirect_hops",
        "connector_run_target_id", "item_id", "file_name", "sha256", "request_count",
        "total_response_bytes", "pid", "appcontainer_sid", "is_appcontainer",
        "loopback_exempt", "job_pids", "tcp_sockets", "udp_sockets",
        "wrapper_start_token_reference",
    }
)
_SENSITIVE_PARTS = frozenset(
    {
        "authorization",
        "cookie",
        "credential",
        "password",
        "secret",
        "token",
        "api_key",
        "raw_headers",
        "subscription_key",
    }
)
_SENSITIVE_TOKENS = frozenset(
    {"authorization", "cookie", "credential", "password", "secret", "token"}
)


class EffectBoundaryHold(RuntimeError):
    """Terminal boundary result containing only an enum and optional digest."""

    def __init__(self, code: str, *, fact_digest: str | None = None) -> None:
        if not isinstance(code, str) or _CODE.fullmatch(code) is None:
            raise ValueError("hold code must be a bounded lowercase enum")
        if fact_digest is not None and (
            not isinstance(fact_digest, str) or _DIGEST.fullmatch(fact_digest) is None
        ):
            raise ValueError("hold fact must be a lowercase SHA-256 digest")
        self.code = code
        self.fact_digest = fact_digest
        public = code if fact_digest is None else f"{code}:{fact_digest}"
        super().__init__(public)


@dataclass(frozen=True)
class WorkerIdentity:
    """Secret-free OS facts attested by a worker and checked by its broker."""

    pid: int
    appcontainer_sid: str
    is_appcontainer: bool
    loopback_exempt: bool
    job_pids: tuple[int, ...]
    tcp_sockets: tuple[str, ...]
    udp_sockets: tuple[str, ...]

    def to_frame(self) -> dict[str, Any]:
        return {
            "type": "worker_attestation",
            "pid": self.pid,
            "appcontainer_sid": self.appcontainer_sid,
            "is_appcontainer": self.is_appcontainer,
            "loopback_exempt": self.loopback_exempt,
            "job_pids": list(self.job_pids),
            "tcp_sockets": list(self.tcp_sockets),
            "udp_sockets": list(self.udp_sockets),
        }

    @classmethod
    def from_frame(cls, payload: Mapping[str, Any]) -> "WorkerIdentity":
        """Parse an attestation without accepting coercions or extra fields."""

        expected = {
            "type",
            "pid",
            "appcontainer_sid",
            "is_appcontainer",
            "loopback_exempt",
            "job_pids",
            "tcp_sockets",
            "udp_sockets",
        }
        if set(payload) != expected or payload.get("type") != "worker_attestation":
            raise EffectBoundaryHold("attestation_malformed")
        pid = payload.get("pid")
        sid = payload.get("appcontainer_sid")
        is_container = payload.get("is_appcontainer")
        exempt = payload.get("loopback_exempt")
        job_pids = payload.get("job_pids")
        tcp = payload.get("tcp_sockets")
        udp = payload.get("udp_sockets")
        if (
            isinstance(pid, bool)
            or not isinstance(pid, int)
            or pid <= 0
            or not isinstance(sid, str)
            or len(sid) > 184
            or not isinstance(is_container, bool)
            or not isinstance(exempt, bool)
            or not _is_int_list(job_pids)
            or not _is_string_list(tcp)
            or not _is_string_list(udp)
        ):
            raise EffectBoundaryHold("attestation_malformed")
        return cls(
            pid=pid,
            appcontainer_sid=sid,
            is_appcontainer=is_container,
            loopback_exempt=exempt,
            job_pids=tuple(job_pids),
            tcp_sockets=tuple(tcp),
            udp_sockets=tuple(udp),
        )


def _is_int_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in value
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and len(item) <= 128 for item in value
    )


def _validate_value(value: object, *, key: str | None = None) -> None:
    if key is not None:
        if key not in _ALLOWED_KEYS:
            raise EffectBoundaryHold("frame_secret_field")
        lowered = key.lower()
        tokens = tuple(part for part in re.split(r"[._-]+", lowered) if part)
        sensitive = lowered in _SENSITIVE_PARTS or any(
            part in _SENSITIVE_TOKENS for part in tokens
        )
        if lowered.endswith("_digest"):
            if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
                raise EffectBoundaryHold("frame_secret_field")
        elif lowered.endswith("_reference"):
            if not isinstance(value, str) or _REFERENCE.fullmatch(value) is None:
                raise EffectBoundaryHold("frame_secret_field")
        elif sensitive:
            raise EffectBoundaryHold("frame_secret_field")
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, list):
        for item in value:
            _validate_value(item)
        return
    if isinstance(value, dict):
        for nested_key, nested in value.items():
            if not isinstance(nested_key, str) or len(nested_key) > 96:
                raise EffectBoundaryHold("frame_invalid_value")
            _validate_value(nested, key=nested_key)
        return
    raise EffectBoundaryHold("frame_invalid_value")


def _validate_payload(payload: object) -> Mapping[str, Any]:
    if not isinstance(payload, dict):
        raise EffectBoundaryHold("frame_not_object")
    _validate_value(payload)
    return payload


def encode_frame(payload: Mapping[str, Any]) -> bytes:
    checked = _validate_payload(payload)
    try:
        body = json.dumps(
            checked,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EffectBoundaryHold("frame_invalid_value") from exc
    if not body or len(body) > MAX_FRAME_BYTES:
        raise EffectBoundaryHold("frame_too_large")
    return struct.pack(">I", len(body)) + body


def decode_frame(frame: bytes) -> dict[str, Any]:
    if not isinstance(frame, bytes) or len(frame) < 4:
        raise EffectBoundaryHold("frame_truncated")
    size = struct.unpack(">I", frame[:4])[0]
    if size > MAX_FRAME_BYTES:
        raise EffectBoundaryHold("frame_too_large")
    if len(frame) < size + 4:
        raise EffectBoundaryHold("frame_truncated")
    if len(frame) > size + 4:
        raise EffectBoundaryHold("frame_trailing_bytes")
    body = frame[4:]
    try:
        payload = json.loads(body.decode("ascii"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError):
        raise EffectBoundaryHold("frame_invalid_json") from None
    canonical = json.dumps(
        payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    if canonical != body:
        raise EffectBoundaryHold("frame_noncanonical_json")
    checked = dict(_validate_payload(payload))
    return checked


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EffectBoundaryHold("frame_duplicate_key")
        result[key] = value
    return result


def read_frame(stream: BinaryIO) -> dict[str, Any]:
    prefix = _read_exact(stream, 4)
    size = struct.unpack(">I", prefix)[0]
    if size > MAX_FRAME_BYTES:
        raise EffectBoundaryHold("frame_too_large")
    return decode_frame(prefix + _read_exact(stream, size))


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not isinstance(chunk, bytes) or not chunk:
            raise EffectBoundaryHold("frame_truncated")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def write_frame(stream: BinaryIO, payload: Mapping[str, Any]) -> None:
    frame = encode_frame(payload)
    written = stream.write(frame)
    if written is not None and written != len(frame):
        raise EffectBoundaryHold("frame_write_incomplete")
    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()


class _EffectExecutor(Protocol):
    def execute(self, plan: PhysicalRequestPlan) -> EffectResult: ...


def _result_header(result: EffectResult, plan: PhysicalRequestPlan) -> dict[str, Any]:
    header_names = result.response_header_names
    valid_headers = (
        isinstance(header_names, tuple)
        and header_names == tuple(sorted(set(header_names)))
        and all(isinstance(name, str) and _HEADER_NAME.fullmatch(name) for name in header_names)
    )
    if (
        not isinstance(result.reservation_event_id, str)
        or result.reservation_event_id != plan.slot_uuid
        or result.plan_digest != plan.plan_digest
        or isinstance(result.status_code, bool)
        or not isinstance(result.status_code, int)
        or not 100 <= result.status_code <= 599
        or not isinstance(result.body, bytes)
        or len(result.body) > plan.limits.max_response_bytes
        or not valid_headers
        or (
            result.redirect_location is not None
            and (not isinstance(result.redirect_location, str) or len(result.redirect_location) > 4096)
        )
    ):
        raise EffectBoundaryHold("effect_result_invalid")
    return {
        "type": "effect_result",
        "reservation_event_id": result.reservation_event_id,
        "plan_digest": result.plan_digest,
        "status_code": result.status_code,
        "response_header_names": list(header_names),
        "redirect_location": result.redirect_location,
        "body_size": len(result.body),
        "body_digest": "sha256:" + hashlib.sha256(result.body).hexdigest(),
    }


def _write_result(stream: BinaryIO, result: EffectResult, plan: PhysicalRequestPlan) -> None:
    write_frame(stream, _result_header(result, plan))
    for index, offset in enumerate(range(0, len(result.body), _BODY_CHUNK_BYTES)):
        chunk = result.body[offset : offset + _BODY_CHUNK_BYTES]
        write_frame(
            stream,
            {
                "type": "effect_body_chunk",
                "index": index,
                "data_b64": base64.b64encode(chunk).decode("ascii"),
            },
        )
    write_frame(stream, {"type": "effect_result_end"})


def _read_result(stream: BinaryIO, plan: PhysicalRequestPlan) -> EffectResult:
    header = read_frame(stream)
    if header.get("type") == "effect_hold":
        if set(header) != {"type", "code"}:
            raise EffectBoundaryHold("effect_hold_malformed")
        code = header.get("code")
        if not isinstance(code, str) or _CODE.fullmatch(code) is None:
            raise EffectBoundaryHold("effect_hold_malformed")
        raise EffectBoundaryHold(code)
    expected = {
        "type", "reservation_event_id", "plan_digest", "status_code",
        "response_header_names", "redirect_location", "body_size", "body_digest",
    }
    if set(header) != expected or header.get("type") != "effect_result":
        raise EffectBoundaryHold("effect_result_malformed")
    event_id = header.get("reservation_event_id")
    plan_digest = header.get("plan_digest")
    status_code = header.get("status_code")
    names = header.get("response_header_names")
    location = header.get("redirect_location")
    body_size = header.get("body_size")
    body_digest = header.get("body_digest")
    if (
        not isinstance(event_id, str)
        or event_id != plan.slot_uuid
        or plan_digest != plan.plan_digest
        or isinstance(status_code, bool)
        or not isinstance(status_code, int)
        or not 100 <= status_code <= 599
        or not isinstance(names, list)
        or names != sorted(set(names))
        or not all(isinstance(name, str) and _HEADER_NAME.fullmatch(name) for name in names)
        or (location is not None and (not isinstance(location, str) or len(location) > 4096))
        or isinstance(body_size, bool)
        or not isinstance(body_size, int)
        or not 0 <= body_size <= plan.limits.max_response_bytes
        or not isinstance(body_digest, str)
        or _REFERENCE.fullmatch(body_digest) is None
    ):
        raise EffectBoundaryHold("effect_result_malformed")
    body = bytearray()
    expected_index = 0
    while len(body) < body_size:
        frame = read_frame(stream)
        if set(frame) != {"type", "index", "data_b64"} or frame.get("type") != "effect_body_chunk":
            raise EffectBoundaryHold("effect_body_malformed")
        index, encoded = frame.get("index"), frame.get("data_b64")
        if index != expected_index or not isinstance(encoded, str):
            raise EffectBoundaryHold("effect_body_malformed")
        try:
            chunk = base64.b64decode(encoded.encode("ascii"), validate=True)
        except (UnicodeError, ValueError):
            raise EffectBoundaryHold("effect_body_malformed") from None
        if (
            not chunk
            or len(chunk) > _BODY_CHUNK_BYTES
            or base64.b64encode(chunk).decode("ascii") != encoded
            or len(body) + len(chunk) > body_size
        ):
            raise EffectBoundaryHold("effect_body_malformed")
        body.extend(chunk)
        expected_index += 1
    if read_frame(stream) != {"type": "effect_result_end"}:
        raise EffectBoundaryHold("effect_result_malformed")
    if "sha256:" + hashlib.sha256(body).hexdigest() != body_digest:
        raise EffectBoundaryHold("effect_body_digest_mismatch")
    try:
        return EffectResult(
            reservation_event_id=event_id,
            plan_digest=plan_digest,
            status_code=status_code,
            body=bytes(body),
            response_header_names=tuple(names),
            redirect_location=location,
        )
    except (ContractHold, TypeError, ValueError):
        raise EffectBoundaryHold("effect_result_malformed") from None


class PipeEffectPort:
    """Worker-side effect port; inherited pipes are its only effect capability."""

    def __init__(self, reader: BinaryIO, writer: BinaryIO) -> None:
        if not hasattr(reader, "read") or not hasattr(writer, "write"):
            raise EffectBoundaryHold("effect_pipe_invalid")
        self._reader = reader
        self._writer = writer
        self._lock = threading.Lock()

    def execute(self, plan: PhysicalRequestPlan) -> EffectResult:
        if not isinstance(plan, PhysicalRequestPlan):
            raise EffectBoundaryHold("effect_plan_invalid")
        if not self._lock.acquire(blocking=False):
            raise EffectBoundaryHold("effect_request_concurrent")
        try:
            write_frame(self._writer, {"type": "effect_request", "plan": plan.to_document()})
            return _read_result(self._reader, plan)
        except EffectBoundaryHold:
            raise
        except (OSError, TypeError, ValueError):
            raise EffectBoundaryHold("effect_pipe_failed") from None
        finally:
            self._lock.release()


class BrokerEffectGuard:
    """Broker-side one-request gate. It never retries a transport effect."""

    def __init__(self, transport: _EffectExecutor) -> None:
        execute = getattr(transport, "execute", None)
        if not callable(execute):
            raise EffectBoundaryHold("broker_transport_invalid")
        self._transport = transport
        self._lock = threading.Lock()

    def serve_one(self, reader: BinaryIO, writer: BinaryIO) -> None:
        if not self._lock.acquire(blocking=False):
            write_frame(writer, {"type": "effect_hold", "code": "broker_request_concurrent"})
            return
        try:
            try:
                request = read_frame(reader)
                if set(request) != {"type", "plan"} or request.get("type") != "effect_request":
                    raise EffectBoundaryHold("effect_request_malformed")
                plan = physical_request_plan_from_document(request.get("plan"))
                result = self._transport.execute(plan)
                _write_result(writer, result, plan)
            except EffectBoundaryHold as exc:
                write_frame(writer, {"type": "effect_hold", "code": exc.code})
            except (ContractHold, OSError, TypeError, ValueError):
                write_frame(writer, {"type": "effect_hold", "code": "effect_request_malformed"})
            except BaseException:
                write_frame(writer, {"type": "effect_hold", "code": "broker_effect_failed"})
        finally:
            self._lock.release()

    def serve_sciencebase(
        self,
        request: Any,
        reader: BinaryIO | None,
        writer: BinaryIO,
        *,
        read_next: Callable[[], dict[str, Any]] | None = None,
        consume_authority: Callable[[], bool] | None = None,
    ) -> Any:
        """Run one bounded ScienceBase worker session and return its artifact."""

        if not callable(consume_authority):
            raise EffectBoundaryHold("authority_consumer_required")
        document = _sciencebase_input_document(request)
        write_frame(writer, {"type": "sciencebase_start", "request": document})
        next_ordinal = 1
        observed_response_bytes = 0
        authorized_download: str | None = None
        max_requests = 3 * (request.max_redirect_hops + 1)
        authority_consumed = False
        if read_next is None:
            if reader is None:
                raise EffectBoundaryHold("effect_pipe_invalid")

            def read_next() -> dict[str, Any]:
                return read_frame(reader)
        while next_ordinal <= max_requests:
            frame = read_next()
            if frame.get("type") == "sciencebase_complete":
                return _read_sciencebase_output(
                    frame, read_next, request, next_ordinal - 1, observed_response_bytes
                )
            try:
                plan = _plan_from_request_frame(frame)
                _bind_sciencebase_plan(plan, request, next_ordinal, authorized_download)
                if not authority_consumed:
                    health_probe = getattr(self._transport, "health_probe", None)
                    if not callable(health_probe) or health_probe(plan) is not True:
                        raise EffectBoundaryHold("sciencebase_health_probe_failed")
                    if consume_authority() is not True:
                        raise EffectBoundaryHold("live_go_required")
                    authority_consumed = True
            except EffectBoundaryHold as exc:
                write_frame(writer, {"type": "effect_hold", "code": exc.code})
                raise
            except (ContractHold, OSError, TypeError, ValueError):
                write_frame(writer, {"type": "effect_hold", "code": "effect_request_malformed"})
                raise EffectBoundaryHold("effect_request_malformed") from None
            except BaseException:
                raise
            if not self._lock.acquire(blocking=False):
                raise EffectBoundaryHold("broker_request_concurrent")
            try:
                try:
                    result = self._transport.execute(plan)
                    _write_result(writer, result, plan)
                    observed_response_bytes += len(result.body)
                    if next_ordinal == 2:
                        authorized_download = _authorized_download_uri(result.body, request)
                except EffectBoundaryHold as exc:
                    write_frame(writer, {"type": "effect_hold", "code": exc.code})
                    raise
                except (ContractHold, OSError, TypeError, ValueError):
                    write_frame(writer, {"type": "effect_hold", "code": "effect_request_malformed"})
                    raise EffectBoundaryHold("effect_request_malformed") from None
                except BaseException:
                    write_frame(writer, {"type": "effect_hold", "code": "broker_effect_failed"})
                    raise EffectBoundaryHold("broker_effect_failed") from None
            finally:
                self._lock.release()
            next_ordinal += 1
        frame = read_next()
        if frame.get("type") != "sciencebase_complete":
            raise EffectBoundaryHold("sciencebase_request_limit")
        return _read_sciencebase_output(
            frame, read_next, request, next_ordinal - 1, observed_response_bytes
        )


def _plan_from_request_frame(frame: Mapping[str, Any]) -> PhysicalRequestPlan:
    if set(frame) != {"type", "plan"} or frame.get("type") != "effect_request":
        raise EffectBoundaryHold("effect_request_malformed")
    try:
        return physical_request_plan_from_document(frame.get("plan"))
    except (ContractHold, TypeError, ValueError):
        raise EffectBoundaryHold("effect_request_malformed") from None


def _bind_sciencebase_plan(
    plan: PhysicalRequestPlan,
    request: Any,
    ordinal: int,
    authorized_download: str | None,
) -> None:
    from urllib.parse import quote

    expected_target = request.connector_run_target_id or request.expected_item_id
    destinations = {
        1: "https://www.sciencebase.gov/catalog/items?q="
        + quote(request.query, safe="-._~")
        + "&format=json",
        2: "https://www.sciencebase.gov/catalog/item/"
        + quote(request.expected_item_id, safe="-._~")
        + "?format=json",
        3: authorized_download,
    }
    stages = {1: "sciencebase_search", 2: "sciencebase_hydrate", 3: "sciencebase_download"}
    empty_body = "sha256:" + hashlib.sha256(b"").hexdigest()
    if (
        plan.envelope_digest != request.envelope_digest
        or plan.campaign_id != request.campaign_id
        or plan.canonical_root != request.canonical_root
        or plan.connector_run_id != request.connector_run_id
        or plan.target_id != expected_target
        or plan.request_ordinal != ordinal
        or plan.authorization_digest != request.authorization_digest
        or plan.grant_digest != request.grant_digest
        or ordinal not in stages
        or plan.stage != stages[ordinal]
        or plan.canonical_destination != destinations[ordinal]
        or plan.limits != request.limits
        or plan.method != "GET"
        or plan.header_names
        or plan.header_value_sha256s
        or plan.body_sha256 != empty_body
    ):
        raise EffectBoundaryHold("sciencebase_plan_binding_mismatch")


def _authorized_download_uri(body: bytes, request: Any) -> str:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise EffectBoundaryHold("sciencebase_hydration_ambiguous")
            result[key] = value
        return result

    try:
        document = json.loads(body.decode("utf-8"), object_pairs_hook=unique)
        files = document.get("files") if isinstance(document, dict) else None
        matches = [
            item for item in files
            if isinstance(item, dict) and item.get("name") == request.expected_file_name
        ] if isinstance(files, list) else []
        uri = matches[0].get("downloadUri") if len(matches) == 1 else None
    except (UnicodeError, json.JSONDecodeError, AttributeError, TypeError):
        uri = None
    if (
        not isinstance(uri, str)
        or not uri.startswith("https://www.sciencebase.gov/")
        or any(character in uri for character in ("#", "\\", "@"))
    ):
        raise EffectBoundaryHold("sciencebase_hydration_ambiguous")
    return uri


def _sciencebase_input_document(request: Any) -> dict[str, Any]:
    if not isinstance(request, ScienceBaseInput):
        raise EffectBoundaryHold("sciencebase_input_malformed")
    document = {
        "query": request.query,
        "expected_item_id": request.expected_item_id,
        "expected_file_name": request.expected_file_name,
        "envelope_digest": request.envelope_digest,
        "campaign_id": request.campaign_id,
        "canonical_root": request.canonical_root,
        "connector_run_id": request.connector_run_id,
        "authorization_digest": request.authorization_digest,
        "grant_digest": request.grant_digest,
        "max_total_bytes": request.max_total_bytes,
        "limits": {
            "timeout_seconds": request.limits.timeout_seconds,
            "max_response_bytes": request.limits.max_response_bytes,
            "max_redirects": request.limits.max_redirects,
        },
        "max_redirect_hops": request.max_redirect_hops,
        "connector_run_target_id": request.connector_run_target_id,
    }
    _sciencebase_input_from_document(document)
    return document


def _sciencebase_input_from_document(document: object) -> Any:
    fields = set(ScienceBaseInput.__dataclass_fields__)
    if not isinstance(document, dict) or set(document) != fields:
        raise EffectBoundaryHold("sciencebase_input_malformed")
    values = dict(document)
    limits = values.get("limits")
    if not isinstance(limits, dict) or set(limits) != set(RequestLimits.__dataclass_fields__):
        raise EffectBoundaryHold("sciencebase_input_malformed")
    for key in ("max_total_bytes", "max_redirect_hops"):
        if isinstance(values.get(key), bool) or not isinstance(values.get(key), int):
            raise EffectBoundaryHold("sciencebase_input_malformed")
    try:
        values["limits"] = RequestLimits(**limits)
        request = ScienceBaseInput(**values)
        _sciencebase_input_document_shape(request)
        return request
    except (TypeError, ValueError):
        raise EffectBoundaryHold("sciencebase_input_malformed") from None


def _sciencebase_input_document_shape(request: Any) -> None:
    text = (
        request.query, request.expected_item_id, request.expected_file_name,
        request.envelope_digest, request.campaign_id, request.canonical_root,
        request.connector_run_id, request.authorization_digest, request.grant_digest,
    )
    if (
        any(not isinstance(value, str) or not value or len(value) > 4096 for value in text)
        or not 0 < request.max_total_bytes <= 2 * 1024 * 1024 * 1024
        or not 0 <= request.max_redirect_hops <= 4
        or (
            request.connector_run_target_id is not None
            and (not isinstance(request.connector_run_target_id, str) or len(request.connector_run_target_id) > 255)
        )
    ):
        raise EffectBoundaryHold("sciencebase_input_malformed")


def run_sciencebase_worker(reader: BinaryIO, writer: BinaryIO) -> None:
    """Worker entry: input/effects/output use only the two inherited pipes."""

    start = read_frame(reader)
    if set(start) != {"type", "request"} or start.get("type") != "sciencebase_start":
        raise EffectBoundaryHold("sciencebase_start_malformed")
    request = _sciencebase_input_from_document(start.get("request"))
    try:
        output = ScienceBaseProducer(PipeEffectPort(reader, writer)).acquire_exact_file(request)
    except EffectBoundaryHold:
        raise
    except BaseException:
        raise EffectBoundaryHold("sciencebase_worker_hold") from None
    write_frame(
        writer,
        {
            "type": "sciencebase_complete",
            "item_id": output.item_id,
            "file_name": output.file_name,
            "sha256": output.sha256,
            "body_size": len(output.content),
            "request_count": output.request_count,
            "total_response_bytes": output.total_response_bytes,
        },
    )
    for index, offset in enumerate(range(0, len(output.content), _BODY_CHUNK_BYTES)):
        write_frame(
            writer,
            {
                "type": "sciencebase_body_chunk",
                "index": index,
                "data_b64": base64.b64encode(
                    output.content[offset : offset + _BODY_CHUNK_BYTES]
                ).decode("ascii"),
            },
        )
    write_frame(writer, {"type": "sciencebase_complete_end"})
    if read_frame(reader) != {"type": "sciencebase_release"}:
        raise EffectBoundaryHold("sciencebase_release_malformed")


def release_sciencebase_worker(writer: BinaryIO) -> None:
    """Release a completed worker only after the broker's fresh OS census."""

    write_frame(writer, {"type": "sciencebase_release"})


def _read_sciencebase_output(
    header: Mapping[str, Any],
    read_next: Callable[[], dict[str, Any]],
    request: Any,
    observed_request_count: int,
    observed_response_bytes: int,
) -> Any:
    expected = {
        "type", "item_id", "file_name", "sha256", "body_size",
        "request_count", "total_response_bytes",
    }
    size = header.get("body_size")
    count = header.get("request_count")
    total = header.get("total_response_bytes")
    if (
        set(header) != expected
        or header.get("item_id") != request.expected_item_id
        or header.get("file_name") != request.expected_file_name
        or not isinstance(header.get("sha256"), str)
        or _DIGEST.fullmatch(header["sha256"]) is None
        or isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= request.max_total_bytes
        or isinstance(count, bool) or not isinstance(count, int) or count != observed_request_count
        or isinstance(total, bool) or not isinstance(total, int) or total != observed_response_bytes
        or not size <= total <= request.max_total_bytes
    ):
        raise EffectBoundaryHold("sciencebase_complete_malformed")
    content = bytearray()
    index = 0
    while len(content) < size:
        frame = read_next()
        if set(frame) != {"type", "index", "data_b64"} or frame.get("type") != "sciencebase_body_chunk" or frame.get("index") != index:
            raise EffectBoundaryHold("sciencebase_complete_malformed")
        encoded = frame.get("data_b64")
        try:
            chunk = base64.b64decode(encoded.encode("ascii"), validate=True) if isinstance(encoded, str) else b""
        except (UnicodeError, ValueError):
            raise EffectBoundaryHold("sciencebase_complete_malformed") from None
        if not chunk or len(chunk) > _BODY_CHUNK_BYTES or len(content) + len(chunk) > size:
            raise EffectBoundaryHold("sciencebase_complete_malformed")
        content.extend(chunk)
        index += 1
    if read_next() != {"type": "sciencebase_complete_end"}:
        raise EffectBoundaryHold("sciencebase_complete_malformed")
    digest = hashlib.sha256(content).hexdigest()
    if header["sha256"] not in {digest, "sha256:" + digest}:
        raise EffectBoundaryHold("sciencebase_complete_digest_mismatch")
    return ScienceBaseOutput(
        item_id=header["item_id"], file_name=header["file_name"], content=bytes(content),
        sha256=digest, request_count=count, total_response_bytes=total,
    )
