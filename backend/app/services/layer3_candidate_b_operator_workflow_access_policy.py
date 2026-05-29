from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Mapping

from app.core.config import settings


POLICY_SCHEMA_ID = "layer3.candidate_b.operator_workflow.owner_access_policy_decision.v1"
POLICY_AUDIT_SCHEMA_ID = "layer3.candidate_b.operator_workflow.ownership_access_audit_event.v1"
POLICY_MODE = "candidate_b_operator_workflow_owner_scoped_access_decision_v1"
PROXY_OWNER_STORAGE_POLICY_RUNTIME = (
    "candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1"
)
AUTH_OWNER_PROXY_TRUSTED_MODE = "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true"
AUTH_OWNER_NONE_LOCAL_MODE = "AUTH_OWNER_none_single_operator_dev_profile"
IDENTITY_AUTHORITY = "server_request_context_configured_proxy_identity_header_hash_only"
TENANT_WORKSPACE_AUTHORITY = (
    "server_request_context_configured_proxy_groups_header_hash_only"
)
STORAGE_ACCESS_POLICY = (
    "configured_workflow_receipt_root_only_receipt_bound_refs_only_no_client_supplied_paths"
)
AUDIT_EVENT_POLICY = "append_only_redacted_policy_receipt_under_configured_workflow_root"
POLICY_RECEIPT_PREFIX = "cb-full-corpus-operator-policy"
LOCAL_ACTOR_REF = "local-single-operator-dev-profile"
LOCAL_TENANT_REF = "local-single-workspace-dev-profile"
OWNER_ROLE = "owner"
AUDITOR_ROLE = "auditor"
OWNER_ALLOWED_ROUTE_FAMILIES = {
    "workflow_run",
    "queue_scheduler_worker_progress_completion_retry",
    "lifecycle_expiry",
    "process_execution",
    "completion_result_adoption",
    "downstream_proof",
    "repeatability_checkpoint",
    "rerun_trial",
    "acceptance_checkpoint",
    "acceptance_closeout",
}
AUDITOR_ALLOWED_ROUTE_FAMILIES = {
    "workflow_history",
    "workflow_status",
    "completion_monitor",
    "closeout_status",
    "review_status_projection",
    "audit_projection",
}
FORBIDDEN_REQUEST_FIELDS = {
    "auth_policy_override",
    "auth_security_directive",
    "security_context",
    "browser_identity",
    "local_storage_identity",
    "proxy_identity_header",
    "raw_operator_identity",
    "raw_tenant_id",
    "raw_workspace_id",
    "operator_role_override",
    "permission_override",
    "raw_storage_root",
    "raw_receipt_path",
    "raw_url",
    "provider_secret",
    "connector_secret",
}

_REQUEST_CONTEXT: ContextVar[Mapping[str, str] | None] = ContextVar(
    "candidate_b_operator_workflow_access_policy_request_context",
    default=None,
)


class CandidateBOperatorWorkflowAccessPolicyError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": POLICY_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "candidate-b-operator-workflow-access-policy-error",
            "server_time": _server_time(),
            "mode": POLICY_MODE,
            "status": "blocked",
            "policy_status": "rejected",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


@contextmanager
def request_context(headers: Mapping[str, str]) -> Iterator[None]:
    token = _REQUEST_CONTEXT.set(_normalise_headers(headers))
    try:
        yield
    finally:
        _REQUEST_CONTEXT.reset(token)


def reject_forbidden_request_fields(fields: Mapping[str, Any]) -> None:
    blocked = sorted(key for key in fields if key in FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_forbidden_request_fields",
            "Candidate B workflow ownership policy rejects caller-supplied auth/security, raw identity, storage root, URL, or credential fields.",
            details={"blocked_fields": blocked},
        )


def authorize_workflow_access(
    *,
    fields: Mapping[str, Any],
    route_family: str,
    rendered_surface: str,
    workflow_receipt_id: str,
    workflow_receipt_hash: str,
    authority_basis_hash: str,
    requested_role: str,
    existing_owner_binding: Mapping[str, Any] | None = None,
    require_existing_owner_binding: bool = True,
) -> dict[str, Any]:
    reject_forbidden_request_fields(fields)
    actor_ref_hash, tenant_or_workspace_ref_hash, role = _server_derived_principal(requested_role)
    _assert_role_allowed(role, route_family)
    _assert_owner_binding(
        role=role,
        actor_ref_hash=actor_ref_hash,
        tenant_or_workspace_ref_hash=tenant_or_workspace_ref_hash,
        existing_owner_binding=existing_owner_binding,
        require_existing_owner_binding=require_existing_owner_binding,
    )
    policy_hash = _policy_hash(
        route_family=route_family,
        rendered_surface=rendered_surface,
        actor_ref_hash=actor_ref_hash,
        tenant_or_workspace_ref_hash=tenant_or_workspace_ref_hash,
        workflow_receipt_hash=workflow_receipt_hash,
        authority_basis_hash=authority_basis_hash,
    )
    requested_policy_hash = str(fields.get("policy_hash") or "").strip()
    if requested_policy_hash and requested_policy_hash != policy_hash:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_stale_policy_hash",
            "The supplied Candidate B workflow ownership policy hash is stale or contradictory.",
            http_status=409,
            details={"expected_policy_hash": policy_hash, "received_policy_hash": requested_policy_hash},
        )
    request_id = str(fields.get("client_request_id") or "candidate-b-operator-workflow-access-policy").strip()
    decision = {
        "policy_schema_id": POLICY_SCHEMA_ID,
        "policy_runtime": PROXY_OWNER_STORAGE_POLICY_RUNTIME,
        "auth_owner_mode": _auth_owner_mode(),
        "identity_authority": IDENTITY_AUTHORITY,
        "tenant_workspace_authority": TENANT_WORKSPACE_AUTHORITY,
        "storage_access_policy": STORAGE_ACCESS_POLICY,
        "audit_event_policy": AUDIT_EVENT_POLICY,
        "policy_hash": policy_hash,
        "policy_status": "admitted",
        "decision": "allow",
        "reason_code": _reason_code(role, route_family),
        "actor_ref_hash": actor_ref_hash,
        "tenant_or_workspace_ref_hash": tenant_or_workspace_ref_hash,
        "workflow_receipt_id": workflow_receipt_id,
        "workflow_receipt_hash": workflow_receipt_hash,
        "route_family": route_family,
        "rendered_surface": rendered_surface,
        "operator_role": role,
    }
    audit_event = _append_audit_event(
        decision=decision,
        request_id=request_id,
        authority_basis_hash=authority_basis_hash,
    )
    return {
        **decision,
        "audit_event_id": audit_event["event_id"],
        "audit_event_hash": audit_event["event_hash"],
        "audit_event_ref": audit_event["event_ref"],
        "next_actions": _next_actions(role, route_family),
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_tenant_or_workspace_exposed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "raw_token_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "artifact_bytes_exposed": False,
        "browser_storage_authority_used": False,
        "frontend_durable_authority_enabled": False,
        "workflow_receipt_owner_binding_required": settings.auth_owner == "proxy",
    }


def owner_binding_from_policy(policy_decision: Mapping[str, Any]) -> dict[str, str]:
    return {
        "actor_ref_hash": str(policy_decision["actor_ref_hash"]),
        "tenant_or_workspace_ref_hash": str(policy_decision["tenant_or_workspace_ref_hash"]),
        "policy_hash": str(policy_decision["policy_hash"]),
    }


def owner_binding_from_workflow_authority(authority: Mapping[str, Any]) -> dict[str, str] | None:
    explicit_binding = authority.get("workflow_receipt_owner_binding")
    if isinstance(explicit_binding, Mapping):
        return {
            "actor_ref_hash": str(explicit_binding.get("actor_ref_hash") or ""),
            "tenant_or_workspace_ref_hash": str(
                explicit_binding.get("tenant_or_workspace_ref_hash") or ""
            ),
            "policy_hash": str(explicit_binding.get("policy_hash") or ""),
        }
    policy_decision = authority.get("ownership_access_policy")
    if isinstance(policy_decision, Mapping):
        return owner_binding_from_policy(policy_decision)
    server_owned_run = authority.get("server_owned_workflow_run")
    if isinstance(server_owned_run, Mapping):
        nested_binding = owner_binding_from_workflow_authority(server_owned_run)
        if nested_binding:
            return nested_binding
    return None


def authorize_history_row_access(
    *,
    fields: Mapping[str, Any],
    row: Mapping[str, Any],
    route_family: str,
    rendered_surface: str,
    requested_role: str = OWNER_ROLE,
) -> dict[str, Any]:
    return authorize_workflow_access(
        fields=fields,
        route_family=route_family,
        rendered_surface=rendered_surface,
        workflow_receipt_id=str(row["operator_workflow_receipt_id"]),
        workflow_receipt_hash=str(row["operator_workflow_receipt_hash"]),
        authority_basis_hash=str(row["authority_basis_hash"]),
        requested_role=str(fields.get("operator_role") or requested_role),
        existing_owner_binding=owner_binding_from_workflow_authority(row),
    )


def authorize_projection_receipt_access(
    *,
    fields: Mapping[str, Any],
    route_family: str,
    rendered_surface: str,
    projection_receipt_id: str,
    projection_receipt_hash: str,
    authority_basis_hash: str,
    existing_owner_binding: Mapping[str, Any] | None,
    requested_role: str = AUDITOR_ROLE,
) -> dict[str, Any]:
    return authorize_workflow_access(
        fields=fields,
        route_family=route_family,
        rendered_surface=rendered_surface,
        workflow_receipt_id=projection_receipt_id,
        workflow_receipt_hash=projection_receipt_hash,
        authority_basis_hash=authority_basis_hash,
        requested_role=str(fields.get("operator_role") or requested_role),
        existing_owner_binding=existing_owner_binding,
        require_existing_owner_binding=True,
    )


def _server_derived_principal(requested_role: str) -> tuple[str, str, str]:
    role = _normalise_role(requested_role)
    if settings.auth_owner == "none":
        return (
            _stable_hash({"auth_owner": "none", "actor_ref": LOCAL_ACTOR_REF}),
            _stable_hash({"auth_owner": "none", "tenant_or_workspace_ref": LOCAL_TENANT_REF}),
            role,
        )
    if settings.auth_owner != "proxy":
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_auth_owner_not_admitted",
            "Candidate B workflow ownership policy admits only AUTH_OWNER=none or AUTH_OWNER=proxy.",
            http_status=409,
        )
    if not settings.trusted_proxy_mode:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_untrusted_proxy_identity",
            "AUTH_OWNER=proxy requires TRUSTED_PROXY_MODE=true before proxy identity can be server authority.",
            http_status=409,
        )
    headers = _REQUEST_CONTEXT.get()
    if not headers:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_missing_identity_authority",
            "Candidate B workflow ownership policy requires server request context when AUTH_OWNER=proxy.",
            http_status=401,
        )
    actor_ref = _required_header(headers, settings.proxy_identity_header, "identity")
    tenant_ref = _required_header(headers, settings.proxy_groups_header, "tenant_or_workspace")
    return (
        _stable_hash({"auth_owner": "proxy", "actor_ref": actor_ref}),
        _stable_hash({"auth_owner": "proxy", "tenant_or_workspace_ref": tenant_ref}),
        role,
    )


def _normalise_role(value: str) -> str:
    role = str(value or "").strip().lower()
    if role in {"", OWNER_ROLE}:
        return OWNER_ROLE
    if role == AUDITOR_ROLE:
        return AUDITOR_ROLE
    raise CandidateBOperatorWorkflowAccessPolicyError(
        "candidate_b_operator_workflow_access_policy_role_not_admitted",
        "Candidate B workflow ownership policy admits only owner and auditor roles.",
        details={"received_role": role},
    )


def _assert_role_allowed(role: str, route_family: str) -> None:
    allowed = OWNER_ALLOWED_ROUTE_FAMILIES if role == OWNER_ROLE else AUDITOR_ALLOWED_ROUTE_FAMILIES
    if route_family not in allowed:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_role_route_forbidden",
            "The operator role is not admitted for the selected Candidate B workflow route family.",
            http_status=403,
            details={"operator_role": role, "route_family": route_family},
        )


def _assert_owner_binding(
    *,
    role: str,
    actor_ref_hash: str,
    tenant_or_workspace_ref_hash: str,
    existing_owner_binding: Mapping[str, Any] | None,
    require_existing_owner_binding: bool,
) -> None:
    if settings.auth_owner != "proxy":
        return
    if not existing_owner_binding:
        if not require_existing_owner_binding:
            return
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_owner_binding_missing",
            "Proxy-owned Candidate B workflow access requires a prior server-owned receipt owner binding.",
            http_status=409,
        )
    expected = {
        "actor_ref_hash": actor_ref_hash,
        "tenant_or_workspace_ref_hash": tenant_or_workspace_ref_hash,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": existing_owner_binding.get(field)}
        for field, expected_value in expected.items()
        if existing_owner_binding.get(field) != expected_value
    ]
    if mismatches:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_cross_owner_receipt",
            "Candidate B workflow ownership policy rejects cross-owner receipt access.",
            http_status=403,
            details={"mismatches": mismatches, "operator_role": role},
        )


def _required_header(headers: Mapping[str, str], configured_name: str, authority_name: str) -> str:
    header_name = str(configured_name or "").strip().lower()
    value = str(headers.get(header_name) or "").strip()
    if not value:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            f"candidate_b_operator_workflow_access_policy_missing_{authority_name}_authority",
            "Candidate B workflow ownership policy requires server-derived identity and tenant/workspace authority.",
            http_status=401,
        )
    return value


def _policy_hash(
    *,
    route_family: str,
    rendered_surface: str,
    actor_ref_hash: str,
    tenant_or_workspace_ref_hash: str,
    workflow_receipt_hash: str,
    authority_basis_hash: str,
) -> str:
    return _stable_hash(
        {
            "selected_auth_mode": PROXY_OWNER_STORAGE_POLICY_RUNTIME,
            "protected_route_family": route_family,
            "protected_rendered_surface": rendered_surface,
            "actor_ref_hash": actor_ref_hash,
            "tenant_or_workspace_ref_hash": tenant_or_workspace_ref_hash,
            "workflow_receipt_hash": workflow_receipt_hash,
            "authority_basis_hash": authority_basis_hash,
            "storage_policy_hash": _stable_hash({"storage": STORAGE_ACCESS_POLICY}),
            "audit_contract_hash": _stable_hash(
                {
                    "audit_event_schema_id": POLICY_AUDIT_SCHEMA_ID,
                    "audit_event_policy": AUDIT_EVENT_POLICY,
                }
            ),
        }
    )


def _append_audit_event(
    *,
    decision: Mapping[str, Any],
    request_id: str,
    authority_basis_hash: str,
) -> dict[str, str]:
    event_input = {
        "schema_id": POLICY_AUDIT_SCHEMA_ID,
        "schema_version": 1,
        "policy_schema_id": POLICY_SCHEMA_ID,
        "policy_runtime": str(decision["policy_runtime"]),
        "auth_owner_mode": str(decision["auth_owner_mode"]),
        "identity_authority": str(decision["identity_authority"]),
        "tenant_workspace_authority": str(decision["tenant_workspace_authority"]),
        "storage_access_policy": str(decision["storage_access_policy"]),
        "audit_event_policy": str(decision["audit_event_policy"]),
        "policy_hash": str(decision["policy_hash"]),
        "actor_ref_hash": str(decision["actor_ref_hash"]),
        "tenant_or_workspace_ref_hash": str(decision["tenant_or_workspace_ref_hash"]),
        "workflow_receipt_id": str(decision["workflow_receipt_id"]),
        "workflow_receipt_hash": str(decision["workflow_receipt_hash"]),
        "route_family": str(decision["route_family"]),
        "rendered_surface": str(decision["rendered_surface"]),
        "decision": str(decision["decision"]),
        "reason_code": str(decision["reason_code"]),
        "request_id": request_id,
        "authority_basis_hash": authority_basis_hash,
    }
    event_hash = _stable_hash(event_input)
    event_id = f"{POLICY_RECEIPT_PREFIX}-{event_hash[:24]}"
    event = {
        **event_input,
        "event_id": event_id,
        "event_hash": event_hash,
        "event_ref": f"candidate-b-operator-workflow-policy://{event_id}/{event_hash[:24]}",
        "created_at": _server_time(),
        "append_only_policy_decision_event": True,
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_tenant_or_workspace_exposed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "raw_token_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "artifact_bytes_exposed": False,
    }
    root = _workflow_receipt_root()
    target = root / event_id / "receipt.json"
    if target.exists():
        existing = _read_event(target)
        if existing.get("event_hash") != event_hash:
            raise CandidateBOperatorWorkflowAccessPolicyError(
                "candidate_b_operator_workflow_access_policy_audit_event_conflict",
                "Candidate B workflow policy audit event storage is stale or contradictory.",
                http_status=409,
            )
        return {
            "event_id": event_id,
            "event_hash": event_hash,
            "event_ref": str(existing["event_ref"]),
        }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(event, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_audit_event_write_failed",
            "Candidate B workflow policy audit event could not be appended.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    return {"event_id": event_id, "event_hash": event_hash, "event_ref": str(event["event_ref"])}


def _read_event(path: Path) -> dict[str, Any]:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_audit_event_unreadable",
            "Candidate B workflow policy audit event could not be read.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    if not isinstance(event, dict):
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_audit_event_invalid",
            "Candidate B workflow policy audit events must be JSON objects.",
            http_status=409,
        )
    return event


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_dir_invalid",
            "Candidate B workflow policy requires an absolute configured workflow receipt directory.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBOperatorWorkflowAccessPolicyError(
            "candidate_b_operator_workflow_access_policy_dir_missing",
            "Candidate B workflow policy requires an existing configured workflow receipt directory.",
            http_status=404,
        )
    return root


def _normalise_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).strip().lower(): str(value).strip() for key, value in headers.items()}


def _auth_owner_mode() -> str:
    if settings.auth_owner == "proxy":
        return AUTH_OWNER_PROXY_TRUSTED_MODE
    return AUTH_OWNER_NONE_LOCAL_MODE


def _reason_code(role: str, route_family: str) -> str:
    return f"{role}_{route_family}_server_policy_allowed"


def _next_actions(role: str, route_family: str) -> list[str]:
    if role == AUDITOR_ROLE:
        return ["inspect redacted Candidate B workflow status, history, review, or audit projections"]
    if route_family == "workflow_run":
        return ["persist or inspect the server-owned Candidate B workflow-run receipt"]
    return ["continue through the admitted Candidate B workflow operator path"]


def _server_time() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
