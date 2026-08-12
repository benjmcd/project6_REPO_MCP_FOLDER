"""One-use owner-GO and closeout path for one bounded ScienceBase acquisition."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Protocol
from uuid import UUID, uuid5

from app.services.connector_egress_transport import ReservationHold
from app.services.dual_live_sciencebase_producer import ScienceBaseOutput


LIVE_GO_SCHEMA = "project6.sciencebase_live_go.v1"
LIVE_EVIDENCE_SCHEMA = "project6.sciencebase_live_evidence.v1"
LIVE_EVENT_NAMESPACE = UUID("b9863662-dd18-58cc-9914-97eb88ad2988")
MAX_LIVE_GO_BYTES = 64 * 1024
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}\Z")
_GO_FIELDS = frozenset(
    {
        "schema",
        "go_id",
        "envelope_digest",
        "campaign_id",
        "canonical_root",
        "connector_run_id",
        "source_commit",
        "interpreter_identity",
        "worker_manifest_digest",
        "request_digest",
        "authorization_digest",
        "grant_digest",
        "wrapper_start_token_ref",
        "credential_mode",
        "egress_mode",
    }
)


class LiveReadinessHold(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class OwnerGoAuthenticator(Protocol):
    """Trusted external authority seam; GO bytes and digest alone grant nothing."""

    def authenticate_exact(self, raw: bytes, content_digest: str) -> bool: ...


@dataclass(frozen=True)
class LiveExecutionResult:
    status: str
    code: str
    artifact_path: Path | None


@dataclass(frozen=True)
class ValidatedLiveGo:
    go_id: str
    content_digest: str
    envelope_digest: str
    campaign_id: str
    canonical_root: str
    connector_run_id: str
    source_commit: str
    interpreter_identity: str
    worker_manifest_digest: str
    request_digest: str
    authorization_digest: str
    grant_digest: str
    wrapper_start_token_ref: str
    credential_mode: str
    egress_mode: str

    @property
    def consumption_event_id(self) -> str:
        return str(uuid5(LIVE_EVENT_NAMESPACE, f"go:{self.connector_run_id}"))

    @property
    def terminal_event_id(self) -> str:
        return str(uuid5(LIVE_EVENT_NAMESPACE, f"terminal:{self.connector_run_id}"))

    @property
    def closeout_event_id(self) -> str:
        return str(uuid5(LIVE_EVENT_NAMESPACE, f"closeout:{self.connector_run_id}"))


def sciencebase_request_digest(request: Any) -> str:
    limits = request.limits
    document = {
        "schema": "project6.sciencebase_request.v1",
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
        "timeout_seconds": limits.timeout_seconds,
        "max_response_bytes": limits.max_response_bytes,
        "max_redirects": limits.max_redirects,
        "max_redirect_hops": request.max_redirect_hops,
        "connector_run_target_id": request.connector_run_target_id,
    }
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _read_bounded(path: Path, limit: int = MAX_LIVE_GO_BYTES) -> bytes:
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError:
        raise LiveReadinessHold("live_go_unreadable") from None
    if len(raw) > limit:
        raise LiveReadinessHold("live_go_too_large")
    return raw


def _strict_document(raw: bytes) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise LiveReadinessHold("live_go_noncanonical")
            result[key] = value
        return result

    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise LiveReadinessHold("live_go_invalid") from None
    if not isinstance(document, dict) or set(document) != _GO_FIELDS:
        raise LiveReadinessHold("live_go_invalid")
    if _canonical(document) != raw:
        raise LiveReadinessHold("live_go_noncanonical")
    return document


def _valid_uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (TypeError, ValueError, AttributeError):
        return False


def load_live_go_once(
    path: Path,
    digest: str,
    prepared: Any,
    *,
    owner_authenticator: OwnerGoAuthenticator | None,
) -> ValidatedLiveGo:
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise LiveReadinessHold("live_go_digest_invalid")
    raw = _read_bounded(path)
    if "sha256:" + hashlib.sha256(raw).hexdigest() != digest:
        raise LiveReadinessHold("live_go_digest_mismatch")
    authenticate = getattr(owner_authenticator, "authenticate_exact", None)
    if not callable(authenticate):
        raise LiveReadinessHold("live_go_owner_authentication_required")
    try:
        authenticated = authenticate(raw, digest)
    except BaseException:
        raise LiveReadinessHold("live_go_owner_authentication_required") from None
    if authenticated is not True:
        raise LiveReadinessHold("live_go_owner_authentication_required")
    document = _strict_document(raw)
    envelope = prepared.envelope.envelope
    expected = {
        "schema": LIVE_GO_SCHEMA,
        "envelope_digest": envelope.content_digest,
        "campaign_id": envelope.campaign_id,
        "canonical_root": envelope.canonical_root,
        "connector_run_id": envelope.connector_run_id,
        "source_commit": envelope.source_commit,
        "interpreter_identity": envelope.interpreter_identity,
        "worker_manifest_digest": prepared.worker_manifest_digest,
        "request_digest": sciencebase_request_digest(prepared.producer_request),
        "authorization_digest": envelope.authorization_digest,
        "grant_digest": envelope.grant_digest,
        "wrapper_start_token_ref": envelope.wrapper_start_token_ref,
        "credential_mode": "none_public",
        "egress_mode": "capability_scoped_default_off",
    }
    if any(document.get(field) != value for field, value in expected.items()):
        raise LiveReadinessHold("live_go_binding_mismatch")
    valid_shapes = (
        _valid_uuid(document.get("go_id"))
        and _valid_uuid(document.get("connector_run_id"))
        and _SHA256.fullmatch(str(document.get("envelope_digest"))) is not None
        and _SHA256.fullmatch(str(document.get("worker_manifest_digest"))) is not None
        and _SHA256.fullmatch(str(document.get("request_digest"))) is not None
        and _SHA256.fullmatch(str(document.get("authorization_digest"))) is not None
        and _SHA256.fullmatch(str(document.get("grant_digest"))) is not None
        and _COMMIT.fullmatch(str(document.get("source_commit"))) is not None
        and _TOKEN.fullmatch(str(document.get("campaign_id"))) is not None
        and _TOKEN.fullmatch(str(document.get("interpreter_identity"))) is not None
        and _TOKEN.fullmatch(str(document.get("wrapper_start_token_ref"))) is not None
        and Path(str(document.get("canonical_root"))).is_absolute()
    )
    if not valid_shapes:
        raise LiveReadinessHold("live_go_invalid")
    return ValidatedLiveGo(
        go_id=str(document["go_id"]),
        content_digest=digest,
        **{field: str(document[field]) for field in expected if field != "schema"},
    )


class OneUseLiveGoConsumer:
    def __init__(self, store: Any, authority: Any) -> None:
        self.store = store
        self.authority = authority
        self.last_code = "live_go_not_consumed"
        self.consumed = False

    def consume_exact(self, envelope_digest: str) -> bool:
        if self.consumed:
            self.last_code = "live_go_already_spent"
            return False
        if envelope_digest != self.authority.envelope_digest:
            self.last_code = "live_go_binding_mismatch"
            return False
        metrics = {
            "schema": LIVE_EVIDENCE_SCHEMA,
            "go_digest": self.authority.content_digest,
            "go_id": self.authority.go_id,
            "envelope_digest": self.authority.envelope_digest,
            "request_digest": self.authority.request_digest,
            "worker_manifest_digest": self.authority.worker_manifest_digest,
            "authorization_digest": self.authority.authorization_digest,
            "grant_digest": self.authority.grant_digest,
            "wrapper_start_token_ref": self.authority.wrapper_start_token_ref,
            "credential_mode": self.authority.credential_mode,
            "egress_mode": self.authority.egress_mode,
            "owner_authentication": "external_capability",
        }
        try:
            result = self.store.write_sciencebase_live_event(
                event_id=self.authority.consumption_event_id,
                connector_run_id=self.authority.connector_run_id,
                phase="live_authority",
                stage="go",
                event_type="sciencebase_live_go_consumed",
                status_after="consumed",
                reason_code="owner_go_consumed",
                metrics=metrics,
            )
        except BaseException:
            self.last_code = "live_go_consumption_indeterminate"
            return False
        disposition = getattr(result, "disposition", "HOLD")
        if disposition == "RECORDED":
            self.consumed = True
            self.last_code = "live_go_consumed"
            return True
        self.last_code = (
            "live_go_already_spent"
            if disposition == "EXISTS"
            else "live_go_consumption_indeterminate"
        )
        return False


def _record_terminal(
    store: Any,
    authority: ValidatedLiveGo,
    *,
    status: str,
    reason_code: str,
    artifact_path: Path | None = None,
    artifact_sha256: str | None = None,
    artifact_bytes: int | None = None,
    request_count: int | None = None,
    total_response_bytes: int | None = None,
    containment_status: str,
) -> bool:
    metrics: dict[str, object] = {
        "schema": LIVE_EVIDENCE_SCHEMA,
        "go_digest": authority.content_digest,
        "envelope_digest": authority.envelope_digest,
        "request_digest": authority.request_digest,
        "credential_mode": authority.credential_mode,
        "egress_mode": authority.egress_mode,
        "containment_status": containment_status,
        "outcome": status,
    }
    if artifact_path is not None:
        metrics.update(
            {
                "artifact_name": artifact_path.name,
                "artifact_sha256": artifact_sha256,
                "artifact_bytes": artifact_bytes,
                "request_count": request_count,
                "total_response_bytes": total_response_bytes,
            }
        )
    result = store.write_sciencebase_live_event(
        event_id=authority.terminal_event_id,
        connector_run_id=authority.connector_run_id,
        phase="terminal",
        stage="sciencebase",
        event_type="sciencebase_acquisition_terminal",
        status_after=status,
        reason_code=reason_code,
        metrics=metrics,
    )
    return getattr(result, "disposition", None) == "RECORDED"


def _write_artifact(
    store: Any,
    authority: ValidatedLiveGo,
    output: ScienceBaseOutput,
    expected_request: Any,
) -> Path:
    content = output.content
    if (
        not isinstance(content, bytes)
        or output.item_id != expected_request.expected_item_id
        or output.file_name != expected_request.expected_file_name
        or output.request_count != 3
        or len(content) > expected_request.limits.max_response_bytes
        or isinstance(output.total_response_bytes, bool)
        or not isinstance(output.total_response_bytes, int)
        or output.total_response_bytes < len(content)
        or output.total_response_bytes > expected_request.max_total_bytes
    ):
        raise LiveReadinessHold("sciencebase_output_invalid")
    digest = hashlib.sha256(content).hexdigest()
    if output.sha256 != digest:
        raise LiveReadinessHold("sciencebase_output_invalid")
    name = f"sciencebase-{authority.content_digest[7:]}-{digest}.bin"
    path = Path(store.canonical_root) / name
    store.verify_identity()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        store.verify_identity()
        with path.open("rb") as handle:
            observed = handle.read(len(content) + 1)
    except (FileExistsError, OSError):
        raise LiveReadinessHold("sciencebase_artifact_write_failed") from None
    if observed != content or hashlib.sha256(observed).hexdigest() != digest:
        raise LiveReadinessHold("sciencebase_artifact_observation_failed")
    return path


def execute_sciencebase_live(
    prepared: Any,
    *,
    go_path: Path,
    go_digest: str,
    run: Callable[..., Any],
    store_factory: Callable[[Path, Path], Any],
    owner_authenticator: OwnerGoAuthenticator | None = None,
) -> LiveExecutionResult:
    try:
        authority = load_live_go_once(
            go_path,
            go_digest,
            prepared,
            owner_authenticator=owner_authenticator,
        )
    except LiveReadinessHold as exc:
        try:
            prepared.reservation_store.close()
        except BaseException:
            pass
        return LiveExecutionResult("HOLD", exc.code, None)
    consumer = OneUseLiveGoConsumer(prepared.reservation_store, authority)
    try:
        output = run(prepared, execution_authority=consumer)
    except BaseException:
        if not consumer.consumed:
            return LiveExecutionResult("HOLD", consumer.last_code, None)
        terminal_store = None
        try:
            root = Path(authority.canonical_root)
            terminal_store = store_factory(root, root / "reservation.db")
            recorded = _record_terminal(
                terminal_store,
                authority,
                status="hold",
                reason_code="sciencebase_execution_failed",
                containment_status="hold_unknown",
            )
            if not recorded:
                return LiveExecutionResult(
                    "HOLD", "sciencebase_terminal_evidence_failed", None
                )
        except BaseException:
            return LiveExecutionResult(
                "HOLD", "sciencebase_terminal_evidence_failed", None
            )
        finally:
            if terminal_store is not None:
                try:
                    terminal_store.close()
                except BaseException:
                    pass
        return LiveExecutionResult("HOLD", "sciencebase_execution_failed", None)
    if not consumer.consumed:
        return LiveExecutionResult("HOLD", consumer.last_code, None)
    terminal_store = None
    try:
        root = Path(authority.canonical_root)
        terminal_store = store_factory(root, root / "reservation.db")
        if not isinstance(output, ScienceBaseOutput):
            raise LiveReadinessHold("sciencebase_output_invalid")
        artifact_path = _write_artifact(
            terminal_store, authority, output, prepared.producer_request
        )
        if not _record_terminal(
            terminal_store,
            authority,
            status="succeeded",
            reason_code="sciencebase_acquisition_succeeded",
            artifact_path=artifact_path,
            artifact_sha256=output.sha256,
            artifact_bytes=len(output.content),
            request_count=output.request_count,
            total_response_bytes=output.total_response_bytes,
            containment_status="contained",
        ):
            return LiveExecutionResult(
                "HOLD", "sciencebase_terminal_evidence_failed", artifact_path
            )
        return LiveExecutionResult(
            "TERMINAL", "sciencebase_acquisition_succeeded", artifact_path
        )
    except LiveReadinessHold as exc:
        try:
            recorded = terminal_store is not None and _record_terminal(
                terminal_store,
                authority,
                status="hold",
                reason_code=exc.code,
                containment_status="contained",
            )
        except BaseException:
            recorded = False
        return LiveExecutionResult(
            "HOLD",
            exc.code if recorded else "sciencebase_terminal_evidence_failed",
            None,
        )
    except BaseException:
        return LiveExecutionResult("HOLD", "sciencebase_terminal_evidence_failed", None)
    finally:
        if terminal_store is not None:
            try:
                terminal_store.close()
            except BaseException:
                pass


def verify_sciencebase_closeout(
    *,
    canonical_root: Path,
    reservation_database_path: Path,
    connector_run_id: str,
    go_digest: str,
    store_factory: Callable[[Path, Path], Any],
) -> LiveExecutionResult:
    root = Path(canonical_root)
    if (
        not root.is_absolute()
        or Path(reservation_database_path) != root / "reservation.db"
        or not isinstance(go_digest, str)
        or _SHA256.fullmatch(go_digest) is None
        or not _valid_uuid(connector_run_id)
    ):
        return LiveExecutionResult("HOLD", "sciencebase_closeout_binding_invalid", None)
    store = None
    try:
        store = store_factory(root, Path(reservation_database_path))
        events = store.read_sciencebase_run_events(connector_run_id)
        if isinstance(events, ReservationHold):
            return LiveExecutionResult("HOLD", events.reason_code, None)
        go_event_id = str(uuid5(LIVE_EVENT_NAMESPACE, f"go:{connector_run_id}"))
        terminal_event_id = str(
            uuid5(LIVE_EVENT_NAMESPACE, f"terminal:{connector_run_id}")
        )
        go_events = [event for event in events if event["event_id"] == go_event_id]
        terminal_events = [
            event for event in events if event["event_id"] == terminal_event_id
        ]
        reservations = [
            event
            for event in events
            if event["event_type"] == "physical_request_reserved"
        ]
        if len(go_events) != 1 or len(terminal_events) != 1:
            return LiveExecutionResult(
                "HOLD", "sciencebase_closeout_evidence_incomplete", None
            )
        go_event = go_events[0]
        terminal = terminal_events[0]
        go_metrics = go_event["metrics"]
        terminal_metrics = terminal["metrics"]
        if not isinstance(go_metrics, dict) or not isinstance(terminal_metrics, dict):
            return LiveExecutionResult(
                "HOLD", "sciencebase_closeout_evidence_malformed", None
            )
        valid_go = (
            go_event["event_type"] == "sciencebase_live_go_consumed"
            and go_event["status_after"] == "consumed"
            and go_event["reason_code"] == "owner_go_consumed"
            and go_metrics.get("schema") == LIVE_EVIDENCE_SCHEMA
            and go_metrics.get("go_digest") == go_digest
            and go_metrics.get("credential_mode") == "none_public"
            and go_metrics.get("egress_mode") == "capability_scoped_default_off"
        )
        expected_reservations = {
            (1, "sciencebase_search"),
            (2, "sciencebase_hydrate"),
            (3, "sciencebase_download"),
        }
        observed_reservations: set[tuple[object, object]] = set()
        reservation_valid = len(reservations) == 3
        for event in reservations:
            metrics = event.get("metrics")
            if not isinstance(metrics, dict):
                reservation_valid = False
                continue
            observed_reservations.add(
                (metrics.get("request_ordinal"), event.get("stage"))
            )
            reservation_valid = reservation_valid and (
                metrics.get("schema") == "project6.physical_request_reservation.v1"
                and metrics.get("envelope_digest")
                == go_metrics.get("envelope_digest")
                and metrics.get("authorization_digest")
                == go_metrics.get("authorization_digest")
                and metrics.get("grant_digest") == go_metrics.get("grant_digest")
                and event.get("status_after") == "reserved"
            )
        reservation_valid = (
            reservation_valid and observed_reservations == expected_reservations
        )
        artifact_name = terminal_metrics.get("artifact_name")
        artifact_sha256 = terminal_metrics.get("artifact_sha256")
        artifact_bytes = terminal_metrics.get("artifact_bytes")
        valid_terminal = (
            terminal["event_type"] == "sciencebase_acquisition_terminal"
            and terminal["status_after"] == "succeeded"
            and terminal["reason_code"] == "sciencebase_acquisition_succeeded"
            and terminal_metrics.get("schema") == LIVE_EVIDENCE_SCHEMA
            and terminal_metrics.get("go_digest") == go_digest
            and terminal_metrics.get("envelope_digest")
            == go_metrics.get("envelope_digest")
            and terminal_metrics.get("request_digest")
            == go_metrics.get("request_digest")
            and terminal_metrics.get("credential_mode") == "none_public"
            and terminal_metrics.get("egress_mode")
            == "capability_scoped_default_off"
            and terminal_metrics.get("containment_status") == "contained"
            and terminal_metrics.get("request_count") == 3
            and isinstance(artifact_name, str)
            and Path(artifact_name).name == artifact_name
            and isinstance(artifact_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", artifact_sha256) is not None
            and artifact_name
            == f"sciencebase-{go_digest[7:]}-{artifact_sha256}.bin"
            and not isinstance(artifact_bytes, bool)
            and isinstance(artifact_bytes, int)
            and 0 <= artifact_bytes <= 64 * 1024 * 1024
        )
        if not valid_go or not reservation_valid or not valid_terminal:
            return LiveExecutionResult(
                "HOLD", "sciencebase_closeout_evidence_malformed", None
            )
        artifact_path = root / artifact_name
        store.verify_identity()
        try:
            with artifact_path.open("rb") as handle:
                content = handle.read(64 * 1024 * 1024 + 1)
        except OSError:
            return LiveExecutionResult(
                "HOLD", "sciencebase_artifact_verification_failed", None
            )
        store.verify_identity()
        if (
            len(content) != artifact_bytes
            or hashlib.sha256(content).hexdigest() != artifact_sha256
        ):
            return LiveExecutionResult(
                "HOLD", "sciencebase_artifact_verification_failed", None
            )
        closeout_metrics = {
            "schema": LIVE_EVIDENCE_SCHEMA,
            "go_digest": go_digest,
            "envelope_digest": go_metrics["envelope_digest"],
            "request_digest": go_metrics["request_digest"],
            "artifact_name": artifact_name,
            "artifact_sha256": artifact_sha256,
            "artifact_bytes": artifact_bytes,
            "reservation_count": 3,
            "credential_mode": "none_public",
            "egress_mode": "capability_scoped_default_off",
            "containment_status": "contained",
        }
        result = store.write_sciencebase_live_event(
            event_id=str(uuid5(LIVE_EVENT_NAMESPACE, f"closeout:{connector_run_id}")),
            connector_run_id=connector_run_id,
            phase="verification",
            stage="closeout",
            event_type="sciencebase_closeout_verified",
            status_after="verified",
            reason_code="sciencebase_closeout_verified",
            metrics=closeout_metrics,
        )
        if getattr(result, "disposition", None) not in {"RECORDED", "EXISTS"}:
            return LiveExecutionResult(
                "HOLD", "sciencebase_closeout_write_failed", artifact_path
            )
        return LiveExecutionResult(
            "VERIFIED", "sciencebase_closeout_verified", artifact_path
        )
    except BaseException:
        return LiveExecutionResult("HOLD", "sciencebase_closeout_failed", None)
    finally:
        if store is not None:
            try:
                store.close()
            except BaseException:
                pass
