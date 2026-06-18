from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services import (
    layer3_sec_xbrl_admission_status,
    layer3_sec_xbrl_auth_binding,
    layer3_sec_xbrl_controlled_value_reveal_submit,
    layer3_sec_xbrl_e2e_integration,
    layer3_sec_xbrl_e2e_offline_orchestrator,
    layer3_sec_xbrl_full_pipeline_orchestrator,
    layer3_sec_xbrl_in_app_auth_policy,
    layer3_sec_xbrl_offline_evidence_loader,
    layer3_sec_xbrl_operator_review_workflow,
    layer3_sec_xbrl_posture,
    layer3_sec_xbrl_projection_persistence,
    layer3_sec_xbrl_statement_packet_persistence,
    layer3_sec_xbrl_value_reveal_authority,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_sec_xbrl_offline_companyfacts_stage import SecXbrlCompanyfactsStageError
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response
from app.api.layer3 import router
from app.api.layer3._shared import *  # noqa: F401,F403
from app.api.layer3 import (
    Layer3SecXbrlControlledValueRevealSubmitRequest,
    Layer3SecXbrlControlledValueRevealSubmitResponse,
    Layer3SecXbrlOperatorReviewDecisionStatusRequest,
    Layer3SecXbrlOperatorReviewDecisionStatusResponse,
    Layer3SecXbrlOperatorReviewDecisionSubmitRequest,
    Layer3SecXbrlOperatorReviewDecisionSubmitResponse,
    Layer3SecXbrlOperatorReviewWorkflowAuditorAttachRequest,
    Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceRequest,
    Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceResponse,
    Layer3SecXbrlOperatorReviewWorkflowOpenFullPipelineRequest,
    Layer3SecXbrlOperatorReviewWorkflowOpenRequest,
    Layer3SecXbrlOperatorReviewWorkflowOpenResponse,
    Layer3SecXbrlOperatorReviewWorkflowStatusRequest,
    Layer3SecXbrlOperatorReviewWorkflowStatusResponse,
    Layer3SecXbrlProductionAdmissionStatusRequest,
    Layer3SecXbrlValueRevealAuthorityPrepareRequest,
    Layer3SecXbrlValueRevealAuthorityPrepareResponse,
    _workbench_error_responses,
)


@router.post(
    "/sec-xbrl/operator-review/workflow/open",
    response_model=Layer3SecXbrlOperatorReviewWorkflowOpenResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_open(
    payload: Layer3SecXbrlOperatorReviewWorkflowOpenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    extra_fields = sorted(str(field) for field in (payload.model_extra or {}))
    if extra_fields:
        return _sec_xbrl_operator_review_workflow_error_response(
            layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_workflow_open_request_fields_not_admitted",
                "SEC XBRL operator review workflow open only admits governed request fields.",
                details={"fields": extra_fields},
                http_status=400,
            )
        )
    try:
        route_family = "sec_xbrl_operator_review_workflow_open_write"
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
        )
        workflow = layer3_sec_xbrl_operator_review_workflow.open_redacted_operator_review_workflow(
            db,
            client_request_id=payload.client_request_id,
            sec_xbrl_statement_packet_set_id=payload.sec_xbrl_statement_packet_set_id,
            commit=False,
        )
        workflow_binding = _sec_xbrl_record_binding(
            db,
            client_request_id=payload.client_request_id,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow["sec_xbrl_operator_review_workflow_id"],
            source_receipt_basis_hash=workflow["workflow_basis_hash"],
            route_family=route_family,
            policy_decision=policy_decision,
            commit=False,
        )
        _sec_xbrl_commit_bound_receipts(db)
        return {
            **base_response(
                workflow["schema_id"],
                request_id=payload.client_request_id,
                status=workflow["status"],
            ),
            **workflow,
            **_sec_xbrl_auth_binding_projection(workflow_binding),
            "workflow_open_api_route_enabled": True,
            "status_api_route_enabled": True,
            "decision_submit_api_route_enabled": True,
            "production_readiness_claimed": False,
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        db.rollback()
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        return _sec_xbrl_operator_review_workflow_error_response(exc)


@router.post(
    "/sec-xbrl/operator-review/workflow/open-from-staged-evidence",
    response_model=Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceResponse,
    responses=_workbench_error_responses(400, 403, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_open_from_staged_evidence(
    payload: Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    extra_fields = sorted(str(field) for field in (payload.model_extra or {}))
    if extra_fields:
        return _sec_xbrl_operator_review_workflow_error_response(
            layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_workflow_open_from_staged_evidence_request_fields_not_admitted",
                "SEC XBRL operator review staged-evidence open only admits governed request fields.",
                details={"fields": extra_fields},
                http_status=400,
            )
        )
    try:
        route_family = "sec_xbrl_operator_review_workflow_open_write"
        policy_decision = _sec_xbrl_policy_decision(request, payload, route_family=route_family)
        # 1) Resolve staged evidence from SERVER storage (never caller path)
        bundle = layer3_sec_xbrl_offline_evidence_loader.load_sec_xbrl_offline_evidence_bundle(
            settings.storage_dir,
            expected_sidecar_receipt_hash=payload.expected_sidecar_receipt_hash,
            expected_statement_classification_receipt_hash=payload.expected_statement_classification_receipt_hash,
            connector_receipt_hash=payload.connector_receipt_hash,
            cik_hash=payload.cik_hash,
        )
        # Oracle-required gate: if the operator opted-in, fail closed when no oracle was supplied.
        if payload.require_companyfacts_oracle and bundle["status"] != "offline_evidence_bundle_ready":
            return _sec_xbrl_staged_evidence_loader_error_response(
                layer3_sec_xbrl_offline_evidence_loader.SecXbrlOfflineEvidenceLoaderError(
                    "sec_xbrl_operator_review_companyfacts_oracle_required",
                    "CompanyFacts oracle is required by this request but was not supplied in the staged evidence bundle.",
                )
            )
        # 1b) Enforce per-principal ownership: caller must have a marker for this sidecar
        layer3_sec_xbrl_auth_binding.require_sec_xbrl_evidence_ownership_marker(
            settings.storage_dir,
            policy_decision=policy_decision,
            auth_owner_mode=str(policy_decision.get("auth_owner_mode") or ""),
            sidecar_receipt_hash=str(bundle["authority_refs"]["sidecar_receipt_hash"]),
        )
        # 2) Compose into open workflow against the REQUEST db, atomic (flush, not commit)
        result = layer3_sec_xbrl_e2e_offline_orchestrator.open_redacted_operator_review_from_offline_evidence(
            db,
            client_request_id=payload.client_request_id,
            evidence=bundle["evidence"],
            period_limit=payload.period_limit,
            single_transaction=True,
            commit=False,
        )
        # 3) Record auth binding on the opened workflow (same kind/family as sibling open route)
        workflow_binding = _sec_xbrl_record_binding(
            db,
            client_request_id=payload.client_request_id,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=result["sec_xbrl_operator_review_workflow_id"],
            source_receipt_basis_hash=result["workflow_basis_hash"],
            route_family=route_family,
            policy_decision=policy_decision,
            commit=False,
        )
        _sec_xbrl_commit_bound_receipts(db)
        return {
            **base_response(
                result["schema_id"],
                request_id=payload.client_request_id,
                status=result["status"],
            ),
            "client_request_id": result["client_request_id"],
            "sec_xbrl_projection_set_id": result["sec_xbrl_projection_set_id"],
            "sec_xbrl_statement_packet_set_id": result["sec_xbrl_statement_packet_set_id"],
            "sec_xbrl_operator_review_workflow_id": result["sec_xbrl_operator_review_workflow_id"],
            "workflow_basis_hash": result.get("workflow_basis_hash"),
            "statement_packet_basis_hash": result.get("statement_packet_basis_hash"),
            "source_projection_basis_hash": result.get("source_projection_basis_hash"),
            "source_report_schema_id": result["source_report_schema_id"],
            "source_report_hash": result.get("source_report_hash"),
            "authority_refs": result["authority_refs"],
            "summary": result["summary"],
            "containment": result["containment"],
            "controls": result["controls"],
            "evidence_bundle_status": bundle["status"],
            **_sec_xbrl_auth_binding_projection(workflow_binding),
            "workflow_open_api_route_enabled": True,
            "status_api_route_enabled": True,
            "decision_submit_api_route_enabled": True,
            "production_readiness_claimed": False,
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        db.rollback()
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_offline_evidence_loader.SecXbrlOfflineEvidenceLoaderError as exc:
        db.rollback()
        return _sec_xbrl_staged_evidence_loader_error_response(exc)
    except layer3_sec_xbrl_e2e_offline_orchestrator.SecXbrlE2EOfflineOrchestratorError as exc:
        db.rollback()
        return _sec_xbrl_staged_evidence_orchestrator_error_response(exc)
    except (
        layer3_sec_xbrl_projection_persistence.SecXbrlProjectionPersistenceError,
        layer3_sec_xbrl_statement_packet_persistence.SecXbrlStatementPacketPersistenceError,
        layer3_sec_xbrl_e2e_integration.SecXbrlE2EIntegrationError,
    ) as exc:
        db.rollback()
        return _sec_xbrl_staged_evidence_persistence_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        db.rollback()
        return _sec_xbrl_operator_review_workflow_error_response(exc)
    except Exception:
        db.rollback()
        raise


def _full_pipeline_leaf_equals_raw_cik(node: Any, raw_ciks: set[str]) -> bool:
    """Recursively report whether any LEAF value equals a raw CIK form.

    Honesty-backstop primitive for the full-pipeline route. Uses VALUE EQUALITY, not a
    substring scan: a genuine leak is a field whose value IS the raw CIK, whereas a numeric
    CIK can appear incidentally inside a 64-char hex hash (a substring scan would false-fire).
    Numeric leaves are normalized to str before comparing so a raw CIK carried as a JSON
    number (e.g. ``"cik": 320193``) is still caught; bool is excluded (it subclasses int).
    """
    if isinstance(node, bool):
        return False
    if isinstance(node, str):
        return node in raw_ciks
    if isinstance(node, int):
        return str(node) in raw_ciks
    if isinstance(node, dict):
        return any(_full_pipeline_leaf_equals_raw_cik(v, raw_ciks) for v in node.values())
    if isinstance(node, (list, tuple)):
        return any(_full_pipeline_leaf_equals_raw_cik(v, raw_ciks) for v in node)
    return False


# Forbidden raw-reference substrings for the full-pipeline honesty backstop. These are
# distinctive enough (unlike a numeric CIK) that a substring scan over the orchestrator's
# own hash-only summaries cannot false-fire: a raw SEC URL or filing-archive path would only
# appear if a raw reference leaked. Defense-in-depth beyond the raw-CIK leaf check.


@router.post(
    "/sec-xbrl/operator-review/workflow/open-full-pipeline",
    response_model=None,
    responses=_workbench_error_responses(400, 403, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_open_full_pipeline(
    payload: Layer3SecXbrlOperatorReviewWorkflowOpenFullPipelineRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    # 1) Auth policy: route-level operator identity + evidence owner stamp
    #    (mirrors the corpus-validation route's gate exactly — this is a write).
    try:
        _route_level_operator_identity(request, access="write")
        owner_stamp = layer3_sec_xbrl_in_app_auth_policy.derive_sec_xbrl_evidence_owner(
            dict(request.headers)
        )
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)

    try:
        # 2) Run steps 1-2 and build the open payload
        plan = layer3_sec_xbrl_full_pipeline_orchestrator.prepare_full_pipeline_open_plan(
            db,
            fields=payload.model_dump(exclude_none=True),
            evidence_owner=owner_stamp,
        )

        # 3) Honesty backstop on the orchestrator's OWN additions (corpus_validation,
        # companyfacts_stage), run BEFORE the open step's commit boundary so a tripped check
        # never leaves a committed workflow behind. These sections are hash-only by
        # construction; assert no leaf VALUE equals the raw CIK (verbatim or zero-stripped).
        # operator_review is NOT scanned here — it is produced by the staged-evidence open
        # handler, which guards its OWN output with redaction checks before ITS commit. The
        # operator-echoed envelope (request_id) is also intentionally out of scope.
        _raw_ciks = {c for c in (payload.cik, str(payload.cik).strip().lstrip("0")) if c}
        _orchestrator_additions = {
            "corpus_validation": plan["corpus_validation"],
            "companyfacts_stage": plan["companyfacts_stage"],
        }
        if _full_pipeline_leaf_equals_raw_cik(_orchestrator_additions, _raw_ciks):
            raise layer3_sec_xbrl_full_pipeline_orchestrator.SecXbrlFullPipelineOrchestratorError(
                "full_pipeline_raw_cik_in_response",
                "Full-pipeline response failed the raw-CIK honesty backstop.",
                http_status=409,
            )
        # Defense-in-depth: also reject raw SEC URLs / filing-archive paths in the
        # orchestrator's own summaries (they are hash-only by construction, so any such
        # marker would indicate a raw-reference leak).
        if _full_pipeline_contains_forbidden_marker(_orchestrator_additions):
            raise layer3_sec_xbrl_full_pipeline_orchestrator.SecXbrlFullPipelineOrchestratorError(
                "full_pipeline_raw_reference_in_response",
                "Full-pipeline response failed the raw-reference honesty backstop.",
                http_status=409,
            )

        # 4) Construct the staged-evidence open request model and call the existing handler.
        # Call via app.api.layer3 so monkeypatch of that attribute is respected in tests.
        import app.api.layer3 as _layer3_pkg
        open_req = Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceRequest(
            **plan["open_payload"]
        )
        open_result = _layer3_pkg.post_sec_xbrl_operator_review_workflow_open_from_staged_evidence(
            open_req, request, db
        )

        # If the open step returned a JSONResponse (error), pass it through as-is.
        if isinstance(open_result, JSONResponse):
            return open_result

        # 5) Compose combined response — no raw CIK, no raw values, hashes only.
        return {
            **base_response(
                layer3_sec_xbrl_full_pipeline_orchestrator.SCHEMA_ID,
                request_id=payload.client_request_id,
                status="full_pipeline_open_ready",
            ),
            "corpus_validation": plan["corpus_validation"],
            "companyfacts_stage": plan["companyfacts_stage"],
            "operator_review": open_result,
            "production_readiness_claimed": False,
        }

    except layer3_sec_xbrl_full_pipeline_orchestrator.SecXbrlFullPipelineOrchestratorError as exc:
        db.rollback()
        return _sec_xbrl_full_pipeline_orchestrator_error_response(exc)
    except SecXbrlCompanyfactsStageError as exc:
        db.rollback()
        return _companyfacts_stage_error_response(exc)
    except Layer3WorkbenchError as exc:
        db.rollback()
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )
    except Exception:
        db.rollback()
        raise


@router.post(
    "/sec-xbrl/operator-review/workflow/status",
    response_model=Layer3SecXbrlOperatorReviewWorkflowStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_status(
    payload: Layer3SecXbrlOperatorReviewWorkflowStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        if payload.sec_xbrl_operator_review_workflow_id is None and payload.workflow_basis_hash is None:
            return layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_workflow_status(
                db,
                **payload.model_dump(exclude={"status_mode", "operator_decision"}, exclude_none=True),
            )
        route_family = "sec_xbrl_operator_review_workflow_status_read"
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
            requested_role=payload.operator_role or layer3_sec_xbrl_in_app_auth_policy.OWNER_ROLE,
        )
        binding = _sec_xbrl_require_binding(
            db,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=payload.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=payload.workflow_basis_hash,
            route_family=route_family,
            policy_decision=policy_decision,
        )
        response = layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_workflow_status(
            db,
            **payload.model_dump(exclude={"status_mode", "operator_decision", "operator_role"}, exclude_none=True),
        )
        return {**response, **_sec_xbrl_auth_binding_projection(binding)}
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        return _sec_xbrl_operator_review_workflow_error_response(exc)


@router.post(
    "/sec-xbrl/operator-review/workflow/admission-status",
    response_model=None,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_admission_status(
    payload: Layer3SecXbrlProductionAdmissionStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    route_family = "sec_xbrl_operator_review_workflow_admission_status_read"
    try:
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
            requested_role=payload.operator_role or layer3_sec_xbrl_in_app_auth_policy.OWNER_ROLE,
        )
        binding = _sec_xbrl_require_binding(
            db,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=payload.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=payload.workflow_basis_hash,
            route_family=route_family,
            policy_decision=policy_decision,
        )
        response = layer3_sec_xbrl_admission_status.inspect_redacted_production_admission_status(
            db,
            client_request_id=payload.client_request_id,
            sec_xbrl_operator_review_workflow_id=payload.sec_xbrl_operator_review_workflow_id,
            workflow_basis_hash=payload.workflow_basis_hash,
            policy_decision=policy_decision,
            auth_owner_mode=str(policy_decision.get("auth_owner_mode") or ""),
        )
        return {**response, **_sec_xbrl_auth_binding_projection(binding)}
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        return _sec_xbrl_operator_review_workflow_error_response(exc)


@router.post(
    "/sec-xbrl/operator-review/workflow/auditor-attach",
    response_model=None,
    responses=_workbench_error_responses(400, 403, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_auditor_attach(
    payload: Layer3SecXbrlOperatorReviewWorkflowAuditorAttachRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """Grant a workspace-scoped, read-only auditor binding for an existing workflow.

    This route mints a ``sec_xbrl_operator_review_workflow_status_read`` auth binding
    with role ``auditor`` for the caller.  It confers NO open/write/decide/value-reveal/
    activation power.  The caller must already have an ownership marker for the sidecar
    hash associated with this workflow's evidence (proving workspace membership).

    Honesty contract:
    - route_family and source_kind are SERVER CONSTANTS — never taken from the payload.
    - The sidecar_receipt_hash is resolved SERVER-SIDE by walking
      workflow → statement_packet_set → projection_set; a caller-supplied hash is
      NEVER accepted.
    - Under AUTH_OWNER=none the owner/auditor distinction is a no-op (constant
      principal) and the grant is only meaningful under AUTH_OWNER=proxy +
      TRUSTED_PROXY_MODE=true.
    - This route does NOT verify a distinct externally-provisioned auditor identity;
      workspace membership (via the ownership marker) is the sole gate.
    """
    # SERVER CONSTANTS — never derived from payload.
    route_family = "sec_xbrl_operator_review_workflow_status_read"
    source_kind = "operator_review_workflow"
    try:
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
            requested_role="auditor",
        )
        # Resolve workflow SERVER-SIDE; never accept a caller-supplied sidecar hash.
        workflow_id = str(payload.sec_xbrl_operator_review_workflow_id or "").strip() or None
        basis_hash = str(payload.workflow_basis_hash or "").strip() or None
        if workflow_id is None and basis_hash is None:
            return _sec_xbrl_auth_policy_error_response(
                layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError(
                    "sec_xbrl_auditor_attach_workflow_anchor_missing",
                    "SEC XBRL auditor attach requires sec_xbrl_operator_review_workflow_id or workflow_basis_hash.",
                    http_status=400,
                )
            )
        try:
            query = db.query(layer3_sec_xbrl_operator_review_workflow.L3SecXbrlOperatorReviewWorkflow)
            if workflow_id is not None:
                query = query.filter(
                    layer3_sec_xbrl_operator_review_workflow.L3SecXbrlOperatorReviewWorkflow.sec_xbrl_operator_review_workflow_id == workflow_id
                )
            if basis_hash is not None:
                query = query.filter(
                    layer3_sec_xbrl_operator_review_workflow.L3SecXbrlOperatorReviewWorkflow.workflow_basis_hash == basis_hash
                )
            workflow = query.one_or_none()
        except Exception as exc:
            return _sec_xbrl_operator_review_workflow_error_response(
                layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                    "sec_xbrl_auditor_attach_workflow_query_failed",
                    "SEC XBRL auditor attach: workflow query failed.",
                    details={"detail": type(exc).__name__},
                    http_status=404,
                )
            )
        if workflow is None:
            return _sec_xbrl_operator_review_workflow_error_response(
                layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                    "sec_xbrl_auditor_attach_workflow_not_found",
                    "SEC XBRL auditor attach: no workflow found for the provided identifier(s).",
                    http_status=404,
                )
            )
        packet_set = workflow.statement_packet_set
        if packet_set is None:
            return _sec_xbrl_operator_review_workflow_error_response(
                layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                    "sec_xbrl_auditor_attach_packet_set_missing",
                    "SEC XBRL auditor attach: workflow has no associated statement packet set.",
                    http_status=404,
                )
            )
        projection_set = packet_set.projection_set
        if projection_set is None:
            return _sec_xbrl_operator_review_workflow_error_response(
                layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                    "sec_xbrl_auditor_attach_projection_set_missing",
                    "SEC XBRL auditor attach: statement packet set has no associated projection set.",
                    http_status=404,
                )
            )
        resolved_sidecar_hash = str(projection_set.sidecar_receipt_hash or "").strip()
        if not resolved_sidecar_hash:
            return _sec_xbrl_operator_review_workflow_error_response(
                layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                    "sec_xbrl_auditor_attach_sidecar_hash_missing",
                    "SEC XBRL auditor attach: projection set has no sidecar receipt hash.",
                    http_status=404,
                )
            )
        # ATTACH GATE: workspace ownership marker must exist for this sidecar.
        # Proves the caller's workspace matches the workflow's evidence workspace.
        layer3_sec_xbrl_auth_binding.require_sec_xbrl_evidence_ownership_marker(
            settings.storage_dir,
            policy_decision=policy_decision,
            auth_owner_mode=str(policy_decision.get("auth_owner_mode") or ""),
            sidecar_receipt_hash=resolved_sidecar_hash,
        )
        # RECORD: write one auditor-role status_read binding receipt.
        # Requires only that the source receipt exists (no prior binding needed).
        binding = _sec_xbrl_record_binding(
            db,
            client_request_id=payload.client_request_id,
            source_receipt_kind=source_kind,
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family=route_family,
            policy_decision=policy_decision,
            commit=True,
        )
        return {
            "sec_xbrl_operator_review_workflow_id": workflow.sec_xbrl_operator_review_workflow_id,
            "workflow_basis_hash": workflow.workflow_basis_hash,
            "status": workflow.review_status,
            **_sec_xbrl_auth_binding_projection(binding),
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        return _sec_xbrl_operator_review_workflow_error_response(exc)


@router.post(
    "/sec-xbrl/operator-review/workflow/decision/submit",
    response_model=Layer3SecXbrlOperatorReviewDecisionSubmitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_decision_submit(
    payload: Layer3SecXbrlOperatorReviewDecisionSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    extra_fields = sorted(str(field) for field in (payload.model_extra or {}))
    if extra_fields:
        return _sec_xbrl_operator_review_workflow_error_response(
            layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_decision_request_fields_not_admitted",
                "SEC XBRL operator review decision submit only admits governed request fields.",
                details={"fields": extra_fields},
                http_status=400,
            )
        )

    payload_data = {
        key: value
        for key, value in payload.model_dump(exclude_none=True).items()
        if key in Layer3SecXbrlOperatorReviewDecisionSubmitRequest.model_fields
    }
    try:
        if payload.sec_xbrl_operator_review_workflow_id is None and payload.workflow_basis_hash is None:
            return layer3_sec_xbrl_operator_review_workflow.record_redacted_operator_review_decision(
                db,
                **{
                    key: value
                    for key, value in payload_data.items()
                    if key not in {"submit_mode", "operator_decision"}
                },
            )
        route_family = "sec_xbrl_operator_review_decision_submit_write"
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
        )
        workflow_binding = _sec_xbrl_require_binding(
            db,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=payload.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=payload.workflow_basis_hash,
            route_family=route_family,
            policy_decision=policy_decision,
        )
        decision = layer3_sec_xbrl_operator_review_workflow.record_redacted_operator_review_decision(
            db,
            **{
                key: value
                for key, value in payload_data.items()
                if key not in {"submit_mode", "operator_decision"}
            },
            commit=False,
        )
        decision_binding = _sec_xbrl_record_binding(
            db,
            client_request_id=payload.client_request_id,
            source_receipt_kind="operator_review_decision",
            source_receipt_id=decision["sec_xbrl_operator_review_decision_id"],
            source_receipt_basis_hash=decision["decision_basis_hash"],
            route_family=route_family,
            policy_decision=policy_decision,
            commit=False,
        )
        _sec_xbrl_commit_bound_receipts(db)
        return {
            **base_response(
                decision["schema_id"],
                request_id=payload.client_request_id,
                status=decision["status"],
            ),
            **decision,
            "source_auth_binding_ref": workflow_binding["auth_binding_ref"],
            **_sec_xbrl_auth_binding_projection(decision_binding),
            "decision_submit_api_route_enabled": True,
            "workflow_open_api_route_enabled": True,
            "rendered_ui_enabled": False,
            "runtime_default_enabled": False,
            "value_reveal_performed": False,
            "delivery_export_enabled": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "production_readiness_claimed": False,
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        db.rollback()
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        return _sec_xbrl_operator_review_workflow_error_response(exc)


@router.post(
    "/sec-xbrl/operator-review/workflow/decision/status",
    response_model=Layer3SecXbrlOperatorReviewDecisionStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_operator_review_workflow_decision_status(
    payload: Layer3SecXbrlOperatorReviewDecisionStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        if payload.sec_xbrl_operator_review_decision_id is None and payload.decision_basis_hash is None:
            return layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_decision_status(
                db,
                **payload.model_dump(exclude={"status_mode", "operator_decision", "operator_role"}, exclude_none=True),
            )
        route_family = "sec_xbrl_operator_review_decision_status_read"
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
            requested_role=payload.operator_role or layer3_sec_xbrl_in_app_auth_policy.OWNER_ROLE,
        )
        try:
            binding = _sec_xbrl_require_binding(
                db,
                source_receipt_kind="operator_review_decision",
                source_receipt_id=payload.sec_xbrl_operator_review_decision_id,
                source_receipt_basis_hash=payload.decision_basis_hash,
                route_family=route_family,
                policy_decision=policy_decision,
            )
        except layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError as phase1_err:
            # Phase-2 fallback for auditor role only.
            # Decision-status needs this explicit workflow-scope fallback because attach
            # mints workflow-scope bindings and the decision is 1:1 with its workflow;
            # admission/workflow-status are natively workflow-scoped and do not need it.
            if policy_decision.get("role") != layer3_sec_xbrl_in_app_auth_policy.AUDITOR_ROLE:
                raise
            try:
                linkage = layer3_sec_xbrl_operator_review_workflow.resolve_operator_review_decision_workflow_linkage(
                    db,
                    sec_xbrl_operator_review_decision_id=payload.sec_xbrl_operator_review_decision_id,
                    decision_basis_hash=payload.decision_basis_hash,
                )
                if linkage is None:
                    raise phase1_err
                workflow_id, workflow_basis_hash = linkage
                policy_decision2 = _sec_xbrl_policy_decision(
                    request,
                    payload,
                    route_family="sec_xbrl_operator_review_workflow_status_read",
                    requested_role=layer3_sec_xbrl_in_app_auth_policy.AUDITOR_ROLE,
                )
                binding = _sec_xbrl_require_binding(
                    db,
                    source_receipt_kind="operator_review_workflow",
                    source_receipt_id=workflow_id,
                    source_receipt_basis_hash=workflow_basis_hash,
                    route_family="sec_xbrl_operator_review_workflow_status_read",
                    policy_decision=policy_decision2,
                )
            except layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError:
                raise phase1_err
            except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError:
                raise phase1_err
            except Exception:
                raise phase1_err
        response = layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_decision_status(
            db,
            **payload.model_dump(exclude={"status_mode", "operator_decision", "operator_role"}, exclude_none=True),
        )
        return {**response, **_sec_xbrl_auth_binding_projection(binding)}
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        return _sec_xbrl_operator_review_workflow_error_response(exc)


@router.post(
    "/sec-xbrl/value-reveal/authority/prepare",
    response_model=Layer3SecXbrlValueRevealAuthorityPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_value_reveal_authority_prepare(
    payload: Layer3SecXbrlValueRevealAuthorityPrepareRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    extra_fields = sorted(str(field) for field in (payload.model_extra or {}))
    if extra_fields:
        return _sec_xbrl_value_reveal_authority_error_response(
            layer3_sec_xbrl_value_reveal_authority.SecXbrlValueRevealAuthorityError(
                "sec_xbrl_value_reveal_authority_request_fields_not_admitted",
                "SEC XBRL value-reveal authority prepare only admits governed request fields.",
                details={"blocked_keys": extra_fields},
                http_status=400,
            )
        )

    payload_data = {
        key: value
        for key, value in payload.model_dump(exclude_none=True).items()
        if key in Layer3SecXbrlValueRevealAuthorityPrepareRequest.model_fields
    }
    try:
        route_family = "sec_xbrl_value_reveal_authority_prepare_write"
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
        )
        decision_binding = _sec_xbrl_require_binding(
            db,
            source_receipt_kind="operator_review_decision",
            source_receipt_id=payload.sec_xbrl_operator_review_decision_id,
            source_receipt_basis_hash=payload.decision_basis_hash,
            route_family=route_family,
            policy_decision=policy_decision,
        )
        receipt = layer3_sec_xbrl_value_reveal_authority.prepare_value_reveal_authority_receipt(
            db,
            **{
                key: value
                for key, value in payload_data.items()
                if key not in {"authority_mode", "operator_decision"}
            },
            commit=False,
        )
        authority_binding = _sec_xbrl_record_binding(
            db,
            client_request_id=payload.client_request_id,
            source_receipt_kind="value_reveal_authority",
            source_receipt_id=receipt["sec_xbrl_value_reveal_authority_receipt_id"],
            source_receipt_basis_hash=receipt["authority_basis_hash"],
            route_family=route_family,
            policy_decision=policy_decision,
            commit=False,
        )
        _sec_xbrl_commit_bound_receipts(db)
        return {
            **base_response(
                receipt["schema_id"],
                request_id=payload.client_request_id,
                status=receipt["status"],
            ),
            **receipt,
            "source_auth_binding_ref": decision_binding["auth_binding_ref"],
            **_sec_xbrl_auth_binding_projection(authority_binding),
            "runtime_default_enabled": False,
            "value_reveal_performed": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "delivery_export_enabled": False,
            "rendered_ui_enabled": False,
            "production_readiness_claimed": False,
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        db.rollback()
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_value_reveal_authority.SecXbrlValueRevealAuthorityError as exc:
        return _sec_xbrl_value_reveal_authority_error_response(exc)


@router.post(
    "/sec-xbrl/value-reveal/submit",
    response_model=Layer3SecXbrlControlledValueRevealSubmitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_xbrl_controlled_value_reveal_submit(
    payload: Layer3SecXbrlControlledValueRevealSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    extra_fields = sorted(str(field) for field in (payload.model_extra or {}))
    if extra_fields:
        return _sec_xbrl_controlled_value_reveal_submit_error_response(
            layer3_sec_xbrl_controlled_value_reveal_submit.SecXbrlControlledValueRevealSubmitError(
                "sec_xbrl_controlled_value_reveal_submit_request_fields_not_admitted",
                "SEC XBRL controlled value-reveal submit only admits authority-receipt request fields.",
                details={"blocked_keys": extra_fields},
                http_status=400,
            )
        )

    payload_data = {
        key: value
        for key, value in payload.model_dump(exclude_none=True).items()
        if key in Layer3SecXbrlControlledValueRevealSubmitRequest.model_fields
    }
    try:
        route_family = "sec_xbrl_controlled_value_reveal_submit_write"
        policy_decision = _sec_xbrl_policy_decision(
            request,
            payload,
            route_family=route_family,
        )
        authority_binding = _sec_xbrl_require_binding(
            db,
            source_receipt_kind="value_reveal_authority",
            source_receipt_id=payload.sec_xbrl_value_reveal_authority_receipt_id,
            source_receipt_basis_hash=payload.authority_basis_hash,
            route_family=route_family,
            policy_decision=policy_decision,
        )
        receipt = layer3_sec_xbrl_controlled_value_reveal_submit.submit_controlled_value_reveal(
            db,
            **{
                key: value
                for key, value in payload_data.items()
                if key not in {"submit_mode", "operator_decision"}
            },
            commit=False,
        )
        submit_binding = _sec_xbrl_record_binding(
            db,
            client_request_id=payload.client_request_id,
            source_receipt_kind="controlled_value_reveal_submit",
            source_receipt_id=receipt["sec_xbrl_controlled_value_reveal_submit_receipt_id"],
            source_receipt_basis_hash=receipt["submit_basis_hash"],
            route_family=route_family,
            policy_decision=policy_decision,
            commit=False,
        )
        _sec_xbrl_commit_bound_receipts(db)
        return {
            **base_response(
                receipt["schema_id"],
                request_id=payload.client_request_id,
                status=receipt["status"],
            ),
            **receipt,
            "source_auth_binding_ref": authority_binding["auth_binding_ref"],
            **_sec_xbrl_auth_binding_projection(submit_binding),
            "runtime_default_enabled": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "delivery_export_enabled": False,
            "rendered_ui_enabled": False,
            "production_readiness_claimed": False,
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        db.rollback()
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_controlled_value_reveal_submit.SecXbrlControlledValueRevealSubmitError as exc:
        return _sec_xbrl_controlled_value_reveal_submit_error_response(exc)


@router.get(
    "/sec-xbrl/value-reveal/submit/status/{sec_xbrl_controlled_value_reveal_submit_receipt_id}",
    response_model=Layer3SecXbrlControlledValueRevealSubmitResponse,
    response_model_exclude_none=True,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_xbrl_controlled_value_reveal_submit_status(
    sec_xbrl_controlled_value_reveal_submit_receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        route_family = "sec_xbrl_controlled_value_reveal_submit_status_read"
        policy_decision = layer3_sec_xbrl_in_app_auth_policy.authorize_sec_xbrl_route(
            headers={str(key): str(value) for key, value in request.headers.items()},
            route_family=route_family,
            requested_role=layer3_sec_xbrl_in_app_auth_policy.OWNER_ROLE,
            request_fields={},
        )
        binding = _sec_xbrl_require_binding(
            db,
            source_receipt_kind="controlled_value_reveal_submit",
            source_receipt_id=sec_xbrl_controlled_value_reveal_submit_receipt_id,
            route_family=route_family,
            policy_decision=policy_decision,
        )
        receipt = layer3_sec_xbrl_controlled_value_reveal_submit.inspect_controlled_value_reveal_submit_status(
            db,
            sec_xbrl_controlled_value_reveal_submit_receipt_id=(
                sec_xbrl_controlled_value_reveal_submit_receipt_id
            ),
        )
        return {
            **base_response(
                receipt["schema_id"],
                request_id=(
                    "sec-xbrl-controlled-value-reveal-status-"
                    f"{sec_xbrl_controlled_value_reveal_submit_receipt_id[:12]}"
                ),
                status=receipt["status"],
            ),
            **receipt,
            **_sec_xbrl_auth_binding_projection(binding),
        }
    except (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError,
        layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError,
    ) as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    except layer3_sec_xbrl_controlled_value_reveal_submit.SecXbrlControlledValueRevealSubmitError as exc:
        return _sec_xbrl_controlled_value_reveal_submit_error_response(exc)


@router.get("/sec-xbrl/identity/projection")
def get_sec_xbrl_proxy_identity_readonly_projection(request: Request) -> dict[str, Any]:
    projection = layer3_sec_xbrl_in_app_auth_policy.build_proxy_identity_readonly_projection(
        headers={str(key): str(value) for key, value in request.headers.items()},
    )
    return {
        **base_response(
            layer3_sec_xbrl_in_app_auth_policy.PROXY_IDENTITY_PROJECTION_SCHEMA_ID,
            request_id="sec-xbrl-identity-projection",
            status=projection["projection_status"],
        ),
        "sec_xbrl_identity_projection": projection,
    }


@router.get("/sec-xbrl/runtime/posture")
def get_sec_xbrl_runtime_posture(request: Request) -> dict[str, Any]:
    try:
        _route_level_operator_identity(request, access="read")
        posture = layer3_sec_xbrl_posture.build_sec_xbrl_runtime_posture()
        return {
            **base_response(
                layer3_sec_xbrl_posture.POSTURE_SCHEMA_ID,
                request_id="sec-xbrl-runtime-posture",
                status=posture["posture_state"],
            ),
            "sec_xbrl_runtime_posture": posture,
        }
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
