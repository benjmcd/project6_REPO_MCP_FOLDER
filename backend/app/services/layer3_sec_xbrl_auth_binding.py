from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    L3SecXbrlAuthBindingReceipt,
    L3SecXbrlControlledValueRevealSubmitReceipt,
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlValueRevealAuthorityReceipt,
)
from app.models.models import (
    L3_SEC_XBRL_AUTH_BINDING_POLICY_ID,
    L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY,
    L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND,
)
from app.services.layer3_sec_xbrl_public_authority_guard import raw_or_local_authority_violation
from app.services.layer3_utils import json_clone, stable_hash


OWNERSHIP_MARKER_SCHEMA_ID = "layer3.sec_xbrl_evidence_ownership_marker.v1"
OWNERSHIP_MARKER_DIR = "layer3-sec-xbrl-evidence-ownership"
# Canonical none-mode auth_owner_mode token — must match exactly for none-mode detection.
# This mirrors the value emitted by layer3_sec_xbrl_in_app_auth_policy._server_derived_principal
# when settings.auth_owner == "none".  Any other token (including proxy-mode tokens that might
# happen to contain the substring "none") must NOT be treated as none-mode.
AUTH_OWNER_MODE_NONE = "AUTH_OWNER_none_single_operator_dev_profile"

AUTH_BINDING_SCHEMA_ID = "layer3.sec_xbrl_auth_binding_receipt.v1"
AUTH_BINDING_MODE = "sec_xbrl_in_app_auth_owner_binding_receipt_v1"
OWNER_ROLE = "owner"
AUDITOR_ROLE = "auditor"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

SOURCE_RECEIPTS = {
    "operator_review_workflow": (
        L3SecXbrlOperatorReviewWorkflow,
        "sec_xbrl_operator_review_workflow_id",
        "workflow_basis_hash",
    ),
    "operator_review_decision": (
        L3SecXbrlOperatorReviewDecision,
        "sec_xbrl_operator_review_decision_id",
        "decision_basis_hash",
    ),
    "value_reveal_authority": (
        L3SecXbrlValueRevealAuthorityReceipt,
        "sec_xbrl_value_reveal_authority_receipt_id",
        "authority_basis_hash",
    ),
    "controlled_value_reveal_submit": (
        L3SecXbrlControlledValueRevealSubmitReceipt,
        "sec_xbrl_controlled_value_reveal_submit_receipt_id",
        "submit_basis_hash",
    ),
}

SOURCE_ROUTE_FAMILIES = {
    "operator_review_workflow": {
        "sec_xbrl_operator_review_workflow_open_write",
        "sec_xbrl_operator_review_workflow_status_read",
        "sec_xbrl_operator_review_workflow_admission_status_read",
        "sec_xbrl_operator_review_decision_submit_write",
    },
    "operator_review_decision": {
        "sec_xbrl_operator_review_decision_submit_write",
        "sec_xbrl_operator_review_decision_status_read",
        "sec_xbrl_value_reveal_authority_prepare_write",
    },
    "value_reveal_authority": {
        "sec_xbrl_value_reveal_authority_prepare_write",
        "sec_xbrl_controlled_value_reveal_submit_write",
    },
    "controlled_value_reveal_submit": {
        "sec_xbrl_controlled_value_reveal_submit_write",
        "sec_xbrl_controlled_value_reveal_submit_status_read",
    },
}

ROUTE_ALLOWED_ROLES = {
    "sec_xbrl_operator_review_workflow_open_write": {OWNER_ROLE},
    "sec_xbrl_operator_review_workflow_status_read": {OWNER_ROLE, AUDITOR_ROLE},
    "sec_xbrl_operator_review_workflow_admission_status_read": {OWNER_ROLE, AUDITOR_ROLE},
    "sec_xbrl_operator_review_decision_submit_write": {OWNER_ROLE},
    "sec_xbrl_operator_review_decision_status_read": {OWNER_ROLE, AUDITOR_ROLE},
    "sec_xbrl_value_reveal_authority_prepare_write": {OWNER_ROLE},
    "sec_xbrl_controlled_value_reveal_submit_write": {OWNER_ROLE},
    "sec_xbrl_controlled_value_reveal_submit_status_read": {OWNER_ROLE},
}

SOURCE_ROUTE_COMPATIBLE_PRIOR_BINDINGS = {
    "operator_review_workflow": {
        "sec_xbrl_operator_review_workflow_status_read": {
            "sec_xbrl_operator_review_workflow_open_write",
        },
        "sec_xbrl_operator_review_workflow_admission_status_read": {
            "sec_xbrl_operator_review_workflow_open_write",
        },
        "sec_xbrl_operator_review_decision_submit_write": {
            "sec_xbrl_operator_review_workflow_open_write",
        },
    },
    "operator_review_decision": {
        "sec_xbrl_operator_review_decision_status_read": {
            "sec_xbrl_operator_review_decision_submit_write",
        },
        "sec_xbrl_value_reveal_authority_prepare_write": {
            "sec_xbrl_operator_review_decision_submit_write",
        },
    },
    "value_reveal_authority": {
        "sec_xbrl_controlled_value_reveal_submit_write": {
            "sec_xbrl_value_reveal_authority_prepare_write",
        },
    },
    "controlled_value_reveal_submit": {
        "sec_xbrl_controlled_value_reveal_submit_status_read": {
            "sec_xbrl_controlled_value_reveal_submit_write",
        },
    },
}

FORBIDDEN_POLICY_KEYS = {
    "actor_ref",
    "workspace_ref",
    "operator_identity",
    "operator_email",
    "operator_name",
    "proxy_authorization",
    "proxy_header",
    "x-forwarded-user",
    "x-forwarded-groups",
    "authorization",
    "token",
    "secret",
    "local_path",
    "raw_path",
    "storage_root",
    "source_url",
    "sec_url",
    "accession",
    "accession_number",
    "cik",
    "company_name",
    "ticker",
    "raw_value",
    "value",
    "amount",
    "effective_value",
    "lexical_value",
    "arelle",
    "source_acquisition",
    "default_on",
    "export",
    "delivery",
}


class SecXbrlAuthBindingError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        http_status: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.http_status = http_status


def record_sec_xbrl_auth_binding(
    db: Session,
    *,
    client_request_id: str,
    source_receipt_kind: str,
    source_receipt_id: str,
    source_receipt_basis_hash: str,
    route_family: str,
    policy_decision: Mapping[str, Any],
    commit: bool = True,
) -> dict[str, Any]:
    request_id = _required_text(client_request_id, "client_request_id")
    _reject_raw_reference(request_id)
    source_kind = _source_kind(source_receipt_kind)
    source_id = _required_text(source_receipt_id, "source_receipt_id")
    _reject_raw_reference(source_id)
    source_basis = _required_hash(source_receipt_basis_hash, "source_receipt_basis_hash")
    route = _route_family(source_kind, route_family)
    policy = _policy_decision(policy_decision, route)
    _load_source_receipt(db, source_kind, source_id, source_basis)

    binding_basis = {
        "binding_schema_id": AUTH_BINDING_SCHEMA_ID,
        "binding_policy_id": L3_SEC_XBRL_AUTH_BINDING_POLICY_ID,
        "source_receipt_kind": source_kind,
        "source_receipt_id": source_id,
        "source_receipt_basis_hash": source_basis,
        "route_family": route,
        "actor_ref_hash": policy["actor_ref_hash"],
        "workspace_ref_hash": policy["workspace_ref_hash"],
        "role": policy["role"],
        "policy_hash": policy["policy_hash"],
    }
    binding_basis_hash = stable_hash(binding_basis)
    summary = _binding_summary(binding_basis)
    negative_invariants = _negative_invariants()

    existing_by_request = (
        db.query(L3SecXbrlAuthBindingReceipt)
        .filter(L3SecXbrlAuthBindingReceipt.client_request_id == request_id)
        .one_or_none()
    )
    existing_by_basis = (
        db.query(L3SecXbrlAuthBindingReceipt)
        .filter(L3SecXbrlAuthBindingReceipt.binding_basis_hash == binding_basis_hash)
        .one_or_none()
    )
    existing_by_route_actor = (
        db.query(L3SecXbrlAuthBindingReceipt)
        .filter(
            L3SecXbrlAuthBindingReceipt.source_receipt_kind == source_kind,
            L3SecXbrlAuthBindingReceipt.source_receipt_id == source_id,
            L3SecXbrlAuthBindingReceipt.route_family == route,
            L3SecXbrlAuthBindingReceipt.actor_ref_hash == policy["actor_ref_hash"],
            L3SecXbrlAuthBindingReceipt.workspace_ref_hash == policy["workspace_ref_hash"],
            L3SecXbrlAuthBindingReceipt.role == policy["role"],
        )
        .one_or_none()
    )
    if existing_by_request is not None:
        if existing_by_request.binding_basis_hash != binding_basis_hash:
            raise SecXbrlAuthBindingError(
                "sec_xbrl_auth_binding_client_request_conflict",
                "client_request_id already recorded a different SEC XBRL auth binding basis.",
                details={"client_request_id": request_id},
            )
        return _response(existing_by_request, idempotent_replay=True)
    if existing_by_basis is not None:
        return _response(existing_by_basis, idempotent_replay=True)
    if existing_by_route_actor is not None:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_source_route_actor_conflict",
            "SEC XBRL source receipt route already has an immutable auth binding for this actor, workspace, and role.",
            details={
                "source_receipt_kind": source_kind,
                "source_receipt_id": source_id,
                "route_family": route,
                "role": policy["role"],
            },
        )

    row = L3SecXbrlAuthBindingReceipt(
        client_request_id=request_id,
        binding_basis_hash=binding_basis_hash,
        binding_schema_id=AUTH_BINDING_SCHEMA_ID,
        binding_policy_id=L3_SEC_XBRL_AUTH_BINDING_POLICY_ID,
        binding_state=L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND,
        source_receipt_kind=source_kind,
        source_receipt_id=source_id,
        source_receipt_basis_hash=source_basis,
        route_family=route,
        actor_ref_hash=policy["actor_ref_hash"],
        workspace_ref_hash=policy["workspace_ref_hash"],
        role=policy["role"],
        policy_hash=policy["policy_hash"],
        redaction_policy=L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY,
        binding_summary_json=summary,
        negative_invariants_json=negative_invariants,
    )
    try:
        db.add(row)
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_integrity_error",
            "SEC XBRL auth binding persistence failed without admitting a partial binding.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(row)
    return _response(row, idempotent_replay=False)


def inspect_sec_xbrl_auth_binding(
    db: Session,
    *,
    source_receipt_kind: str,
    source_receipt_id: str | None = None,
    source_receipt_basis_hash: str | None = None,
    route_family: str | None = None,
    role: str | None = None,
    actor_ref_hash: str | None = None,
    workspace_ref_hash: str | None = None,
) -> dict[str, Any]:
    source_kind = _source_kind(source_receipt_kind)
    query = db.query(L3SecXbrlAuthBindingReceipt).filter(
        L3SecXbrlAuthBindingReceipt.source_receipt_kind == source_kind,
    )
    if source_receipt_id:
        query = query.filter(L3SecXbrlAuthBindingReceipt.source_receipt_id == source_receipt_id)
    if source_receipt_basis_hash:
        query = query.filter(L3SecXbrlAuthBindingReceipt.source_receipt_basis_hash == source_receipt_basis_hash)
    if route_family:
        query = query.filter(L3SecXbrlAuthBindingReceipt.route_family == _route_family(source_kind, route_family))
    if role:
        query = query.filter(L3SecXbrlAuthBindingReceipt.role == _role(role))
    if actor_ref_hash:
        query = query.filter(
            L3SecXbrlAuthBindingReceipt.actor_ref_hash == _required_hash(actor_ref_hash, "actor_ref_hash")
        )
    if workspace_ref_hash:
        query = query.filter(
            L3SecXbrlAuthBindingReceipt.workspace_ref_hash == _required_hash(
                workspace_ref_hash,
                "workspace_ref_hash",
            )
        )
    if not source_receipt_id and not source_receipt_basis_hash:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_lookup_anchor_missing",
            "SEC XBRL auth binding inspection requires source receipt id or basis hash.",
            http_status=400,
        )
    rows = (
        query.order_by(
            L3SecXbrlAuthBindingReceipt.route_family,
            L3SecXbrlAuthBindingReceipt.role,
            L3SecXbrlAuthBindingReceipt.actor_ref_hash,
            L3SecXbrlAuthBindingReceipt.workspace_ref_hash,
            L3SecXbrlAuthBindingReceipt.created_at,
        )
        .all()
    )
    if not rows:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_missing",
            "SEC XBRL auth binding receipt was not found.",
            details={"source_receipt_kind": source_kind},
            http_status=404,
        )
    if len(rows) == 1:
        return _response(rows[0], idempotent_replay=False)
    return {
        "schema_id": AUTH_BINDING_SCHEMA_ID,
        "auth_binding_mode": AUTH_BINDING_MODE,
        "inspection_state": "multiple_bindings",
        "binding_count": len(rows),
        "bindings": [_response(row, idempotent_replay=False) for row in rows],
        "source_receipt_kind": source_kind,
        "source_receipt_basis_hash": source_receipt_basis_hash,
        "source_receipt_id_exposed": False,
        "runtime_auth_dependency_installed": False,
        "api_route_behavior_changed": False,
        "value_reveal_performed": False,
        "runtime_default_enabled": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_or_export_performed": False,
        "production_readiness_claimed": False,
    }


def require_sec_xbrl_owner_binding(
    db: Session,
    *,
    source_receipt_kind: str,
    source_receipt_id: str | None = None,
    source_receipt_basis_hash: str | None = None,
    route_family: str,
    policy_decision: Mapping[str, Any],
) -> dict[str, Any]:
    source_kind = _source_kind(source_receipt_kind)
    route = _route_family(source_kind, route_family)
    policy = _policy_decision(policy_decision, route)
    source_id = str(source_receipt_id or "").strip() or None
    source_basis = str(source_receipt_basis_hash or "").strip() or None
    if source_id is not None:
        _reject_raw_reference(source_id)
    if source_id is None and source_basis is None:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_lookup_anchor_missing",
            "SEC XBRL protected access requires source receipt id or basis hash.",
            details={"source_receipt_kind": source_kind},
            http_status=400,
        )
    compatible_routes = _compatible_route_families(source_kind, route)
    query = db.query(L3SecXbrlAuthBindingReceipt).filter(
        L3SecXbrlAuthBindingReceipt.source_receipt_kind == source_kind,
        L3SecXbrlAuthBindingReceipt.route_family.in_(compatible_routes),
        L3SecXbrlAuthBindingReceipt.actor_ref_hash == policy["actor_ref_hash"],
        L3SecXbrlAuthBindingReceipt.workspace_ref_hash == policy["workspace_ref_hash"],
        L3SecXbrlAuthBindingReceipt.role == policy["role"],
    )
    if source_id is not None:
        query = query.filter(L3SecXbrlAuthBindingReceipt.source_receipt_id == source_id)
    if source_basis is not None:
        if not HASH_RE.fullmatch(source_basis):
            raise SecXbrlAuthBindingError(
                "sec_xbrl_auth_binding_source_receipt_basis_hash_invalid",
                "SEC XBRL protected access requires source receipt basis hash as a 64-character hex hash.",
                details={"source_receipt_kind": source_kind},
                http_status=400,
            )
        query = query.filter(L3SecXbrlAuthBindingReceipt.source_receipt_basis_hash == source_basis)
    rows = query.all()
    exact_rows = [candidate for candidate in rows if candidate.route_family == route]
    if exact_rows:
        row = exact_rows[0]
    elif len(rows) == 1:
        row = rows[0]
    else:
        row = None
    if row is None:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_missing",
            "SEC XBRL protected access requires a prior source receipt auth binding.",
            details={
                "source_receipt_kind": source_kind,
                "source_receipt_id": source_id,
                "source_receipt_basis_hash": source_basis,
            },
            http_status=404,
        )
    mismatches = []
    if row.route_family == route and row.policy_hash not in policy["compatible_policy_hashes"]:
        mismatches.append("policy_hash")
    if mismatches:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_context_mismatch",
            "SEC XBRL auth binding rejects missing, stale, route-mismatched, or cross-owner access.",
            details={"mismatched_fields": mismatches},
            http_status=403,
        )
    return _response(row, idempotent_replay=False)


def record_sec_xbrl_evidence_ownership_marker(
    storage_dir: str | Path,
    *,
    owner_ref_hash: str,
    workspace_ref_hash: str,
    sidecar_receipt_hash: str,
) -> None:
    """Write a per-principal ownership marker file for a staged sidecar.

    Marker path: {storage_dir}/layer3-sec-xbrl-evidence-ownership/
                 {workspace_ref_hash}/sidecar-{sidecar_receipt_hash}.json

    Idempotent: if the file already exists with the same owner_ref_hash, this is a no-op.
    Different workspaces produce distinct marker files for the same sidecar_receipt_hash,
    so deduplication cannot cause cross-workspace collision.

    Skipped silently when owner_ref_hash or workspace_ref_hash are empty.
    """
    owner = str(owner_ref_hash or "").strip()
    workspace = str(workspace_ref_hash or "").strip()
    sidecar_hash = str(sidecar_receipt_hash or "").strip()
    if not owner or not workspace:
        return
    if not HASH_RE.fullmatch(sidecar_hash):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_evidence_ownership_marker_sidecar_hash_invalid",
            "SEC XBRL evidence ownership marker requires sidecar_receipt_hash as a 64-character hex hash.",
            http_status=400,
        )
    if not HASH_RE.fullmatch(owner):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_evidence_ownership_marker_owner_hash_invalid",
            "SEC XBRL evidence ownership marker requires owner_ref_hash as a 64-character hex hash.",
            http_status=400,
        )
    if not HASH_RE.fullmatch(workspace):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_evidence_ownership_marker_workspace_hash_invalid",
            "SEC XBRL evidence ownership marker requires workspace_ref_hash as a 64-character hex hash.",
            http_status=400,
        )
    marker_dir = Path(storage_dir).resolve() / OWNERSHIP_MARKER_DIR / workspace
    marker_path = marker_dir / f"sidecar-{sidecar_hash}.json"
    if marker_path.exists():
        # Workspace-level idempotency: any existing marker for this (workspace, sidecar) pair
        # is a no-op success regardless of the stored owner_ref_hash.  The first staging actor's
        # owner is kept as audit metadata; a second teammate re-staging the same content in the
        # same workspace must NOT produce a conflict.
        return
    marker = {
        "schema_id": OWNERSHIP_MARKER_SCHEMA_ID,
        "owner_ref_hash": owner,
        "workspace_ref_hash": workspace,
        "evidence_kind": "sidecar",
        "sidecar_receipt_hash": sidecar_hash,
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    marker_dir.mkdir(parents=True, exist_ok=True)
    try:
        with marker_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(marker, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        pass  # concurrent write of same marker — idempotent


def require_sec_xbrl_evidence_ownership_marker(
    storage_dir: str | Path,
    *,
    policy_decision: Mapping[str, Any],
    auth_owner_mode: str,
    sidecar_receipt_hash: str,
) -> None:
    """Enforce workspace-level ownership marker check at the open route.

    Looks for {storage_dir}/layer3-sec-xbrl-evidence-ownership/
               {caller_workspace_ref_hash}/sidecar-{sidecar_receipt_hash}.json

    Decision matrix (WORKSPACE-LEVEL — owner_ref_hash is audit metadata only):
      - Marker exists for caller's workspace + sidecar → OK (intra-workspace sharing allowed)
      - No marker present:
          auth_owner_mode == AUTH_OWNER_MODE_NONE → OK (legacy / constant-workspace path)
          else (proxy) → raise 403 marker_missing
      - owner_ref_hash stored in marker is NOT compared to caller (teammates share workspace)

    Path-traversal guard: sidecar_receipt_hash and workspace_ref_hash validated as 64-hex
    before path construction.
    """
    sidecar_hash = str(sidecar_receipt_hash or "").strip()
    if not HASH_RE.fullmatch(sidecar_hash):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_evidence_ownership_marker_sidecar_hash_invalid",
            "SEC XBRL evidence ownership marker check requires sidecar_receipt_hash as a 64-character hex hash.",
            http_status=400,
        )
    caller_workspace = str(policy_decision.get("workspace_ref_hash") or "").strip()
    # L2: Exact token match — prevents a proxy-mode token containing the substring "none"
    # from wrongly enabling the allow-without-marker path.
    is_none_mode = str(auth_owner_mode or "").strip() == AUTH_OWNER_MODE_NONE
    # L1: Validate caller_workspace against HASH_RE before using it in path construction.
    # Mirror record_'s guard to prevent path traversal via a malformed workspace_ref_hash.
    if not is_none_mode and caller_workspace and not HASH_RE.fullmatch(caller_workspace):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_evidence_ownership_marker_workspace_hash_invalid",
            "SEC XBRL evidence ownership marker check requires workspace_ref_hash as a 64-character hex hash.",
            http_status=403,
        )

    marker_path = (
        Path(storage_dir).resolve()
        / OWNERSHIP_MARKER_DIR
        / caller_workspace
        / f"sidecar-{sidecar_hash}.json"
    )
    if not marker_path.exists():
        if is_none_mode:
            return  # none-mode: no marker required (constant workspace)
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_evidence_ownership_marker_missing",
            "SEC XBRL evidence ownership marker is missing; the caller did not stage this evidence.",
            http_status=403,
        )

    # Marker file is present — validate it is a regular file, readable, and has correct fields.
    # Fail-closed under proxy; allow (legacy / no-valid-marker == no marker) under none.
    def _marker_invalid() -> None:
        """Raise 403 under proxy; return silently under none (treat as absent)."""
        if not is_none_mode:
            raise SecXbrlAuthBindingError(
                "sec_xbrl_auth_binding_evidence_ownership_marker_invalid",
                "SEC XBRL evidence ownership marker is present but invalid (not a regular file, "
                "unreadable, or field mismatch); cannot authorize.",
                http_status=403,
            )

    if not marker_path.is_file():
        # e.g. a directory named sidecar-<hash>.json
        _marker_invalid()
        return  # none-mode: treat malformed-as-absent → allow

    try:
        raw = marker_path.read_text(encoding="utf-8")
        parsed: dict[str, Any] = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        _marker_invalid()
        return  # none-mode: treat unreadable/non-JSON as absent → allow

    # Field validation: schema_id, workspace_ref_hash, sidecar_receipt_hash must all match.
    # owner_ref_hash is NOT compared (workspace-level sharing: teammates share marker).
    if (
        parsed.get("schema_id") != OWNERSHIP_MARKER_SCHEMA_ID
        or parsed.get("workspace_ref_hash") != caller_workspace
        or parsed.get("sidecar_receipt_hash") != sidecar_hash
    ):
        _marker_invalid()
        return  # none-mode: treat field-mismatch as absent → allow

    # All checks passed — authorized.


def _source_kind(value: str) -> str:
    source_kind = _required_text(value, "source_receipt_kind")
    if source_kind not in SOURCE_RECEIPTS:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_source_kind_not_admitted",
            "SEC XBRL auth binding admits only known governed SEC XBRL source receipt kinds.",
            details={"source_receipt_kind": source_kind},
            http_status=400,
        )
    return source_kind


def _route_family(source_kind: str, value: str) -> str:
    route = _required_text(value, "route_family")
    if route not in SOURCE_ROUTE_FAMILIES[source_kind]:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_route_family_not_admitted",
            "SEC XBRL auth binding route family is not admitted for the selected source receipt kind.",
            details={"source_receipt_kind": source_kind, "route_family": route},
            http_status=400,
        )
    return route


def _compatible_route_families(source_kind: str, route_family: str) -> tuple[str, ...]:
    compatible = SOURCE_ROUTE_COMPATIBLE_PRIOR_BINDINGS.get(source_kind, {}).get(route_family, set())
    return tuple(dict.fromkeys([route_family, *sorted(compatible)]))


def _role(value: str) -> str:
    role = _required_text(value, "role").lower()
    if role not in {OWNER_ROLE, AUDITOR_ROLE}:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_role_not_admitted",
            "SEC XBRL auth binding admits only owner and auditor roles.",
            details={"role": role},
            http_status=403,
        )
    return role


def _policy_decision(policy_decision: Mapping[str, Any], route_family: str) -> dict[str, Any]:
    if not isinstance(policy_decision, Mapping):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_policy_decision_missing",
            "SEC XBRL auth binding requires a server-derived policy decision.",
            http_status=400,
        )
    blocked_fields = sorted(
        str(key)
        for key, value in policy_decision.items()
        if str(key).lower() in FORBIDDEN_POLICY_KEYS and value is not None
    )
    if blocked_fields:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_policy_raw_fields_not_admitted",
            "SEC XBRL auth binding rejects caller-supplied auth, identity, local path, value, source, Arelle, default, or export fields.",
            details={"blocked_fields": blocked_fields},
            http_status=400,
        )
    decision = _required_text(policy_decision.get("decision"), "policy_decision").lower()
    if decision != "allow":
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_policy_not_admitted",
            "SEC XBRL auth binding requires an admitted server-derived policy decision.",
            details={"decision": decision},
            http_status=403,
        )
    policy_route = _required_text(policy_decision.get("route_family"), "policy_route_family")
    if policy_route != route_family:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_policy_route_mismatch",
            "SEC XBRL auth binding policy route family does not match the source binding route.",
            details={"policy_route_family": policy_route, "route_family": route_family},
            http_status=403,
        )
    role = _role(str(policy_decision.get("role") or ""))
    if role not in ROUTE_ALLOWED_ROLES[route_family]:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_role_route_forbidden",
            "SEC XBRL auth binding does not admit the requested role for this route family.",
            details={"role": role, "route_family": route_family},
            http_status=403,
        )
    return {
        "actor_ref_hash": _required_hash(policy_decision.get("actor_ref_hash"), "actor_ref_hash"),
        "workspace_ref_hash": _required_hash(policy_decision.get("workspace_ref_hash"), "workspace_ref_hash"),
        "role": role,
        "policy_hash": _required_hash(policy_decision.get("policy_hash"), "policy_hash"),
        "compatible_policy_hashes": _compatible_policy_hashes(policy_decision),
    }


def _compatible_policy_hashes(policy_decision: Mapping[str, Any]) -> tuple[str, ...]:
    hashes = [_required_hash(policy_decision.get("policy_hash"), "policy_hash")]
    for index, value in enumerate(policy_decision.get("compatible_policy_hashes") or []):
        hashes.append(_required_hash(value, f"compatible_policy_hashes_{index}"))
    return tuple(dict.fromkeys(hashes))


def _load_source_receipt(
    db: Session,
    source_kind: str,
    source_id: str,
    source_basis_hash: str,
) -> Any:
    model, id_column, basis_column = SOURCE_RECEIPTS[source_kind]
    row = (
        db.query(model)
        .filter(
            getattr(model, id_column) == source_id,
            getattr(model, basis_column) == source_basis_hash,
        )
        .one_or_none()
    )
    if row is None:
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_source_receipt_missing",
            "SEC XBRL auth binding requires an existing source receipt with matching kind, id, and basis hash.",
            details={
                "source_receipt_kind": source_kind,
                "source_receipt_id": source_id,
                "source_receipt_basis_hash": source_basis_hash,
            },
            http_status=404,
        )
    return row


def _binding_summary(binding_basis: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "auth_binding_mode": AUTH_BINDING_MODE,
        "source_receipt_kind": str(binding_basis["source_receipt_kind"]),
        "source_receipt_basis_hash": str(binding_basis["source_receipt_basis_hash"]),
        "route_family": str(binding_basis["route_family"]),
        "role": str(binding_basis["role"]),
        "binding_policy_id": L3_SEC_XBRL_AUTH_BINDING_POLICY_ID,
        "redaction_policy": L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY,
        "hash_only_actor_workspace_refs": True,
        "source_receipt_id_exposed": False,
        "raw_operator_identity_exposed": False,
        "raw_workspace_identity_exposed": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "raw_operator_identity_persisted": False,
        "raw_workspace_identity_persisted": False,
        "raw_proxy_headers_persisted": False,
        "raw_values_persisted": False,
        "residual_magnitudes_persisted": False,
        "local_paths_persisted": False,
        "sec_accessions_or_urls_persisted": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "value_reveal_default_enabled": False,
        "delivery_or_export_performed": False,
    }


def _response(row: L3SecXbrlAuthBindingReceipt, *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "schema_id": AUTH_BINDING_SCHEMA_ID,
        "auth_binding_mode": AUTH_BINDING_MODE,
        "sec_xbrl_auth_binding_receipt_id": row.sec_xbrl_auth_binding_receipt_id,
        "auth_binding_ref": f"sec-xbrl-auth-binding:{row.sec_xbrl_auth_binding_receipt_id}",
        "binding_basis_hash": row.binding_basis_hash,
        "binding_policy_id": row.binding_policy_id,
        "binding_state": row.binding_state,
        "source_receipt_kind": row.source_receipt_kind,
        "source_receipt_basis_hash": row.source_receipt_basis_hash,
        "route_family": row.route_family,
        "actor_ref_hash": row.actor_ref_hash,
        "workspace_ref_hash": row.workspace_ref_hash,
        "role": row.role,
        "policy_hash": row.policy_hash,
        "redaction_policy": row.redaction_policy,
        "binding_summary": json_clone(row.binding_summary_json),
        "negative_invariants": json_clone(row.negative_invariants_json),
        "idempotent_replay": idempotent_replay,
        "runtime_auth_dependency_installed": False,
        "api_route_behavior_changed": False,
        "value_reveal_performed": False,
        "runtime_default_enabled": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_or_export_performed": False,
        "production_readiness_claimed": False,
    }


def _required_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlAuthBindingError(
            f"sec_xbrl_auth_binding_{field_name}_missing",
            f"SEC XBRL auth binding requires {field_name}.",
            http_status=400,
        )
    return text


def _reject_raw_reference(value: str) -> None:
    text = str(value or "").strip()
    if raw_or_local_authority_violation(
        text,
        raw_value_keys=frozenset(),
        raw_authority_keys=frozenset(),
        scan_raw_period_dates=False,
        scan_cik=True,
        scan_contextual_cik=True,
        scan_operator_contact=True,
        scan_bare_sec_domain=True,
        scan_standard_local_refs=False,
        scan_windows_abs_path_anywhere=True,
        scan_local_ref_segment=True,
    ):
        raise SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_raw_reference_not_admitted",
            "SEC XBRL auth binding rejects raw local paths, SEC URLs, CIKs, and SEC accession-like receipt references.",
            http_status=400,
        )


def _required_hash(value: Any, field_name: str) -> str:
    text = _required_text(value, field_name)
    if not HASH_RE.fullmatch(text):
        raise SecXbrlAuthBindingError(
            f"sec_xbrl_auth_binding_{field_name}_invalid",
            f"SEC XBRL auth binding requires {field_name} as a 64-character hex hash.",
            details={field_name: text},
            http_status=400,
        )
    return text
