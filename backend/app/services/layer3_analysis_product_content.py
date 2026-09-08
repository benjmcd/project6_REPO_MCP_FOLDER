"""Read one selected product's authored text and bounded evidence identities.

Authored text is an explicit disclosure to the existing Layer 3 reader audience.
No artifact values, locators, or free-form provenance are loaded or dereferenced.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisProduct, L3AnalysisProductEvidenceLink
from app.services.layer3_analysis_product_authoring import (
    Layer3AnalysisProductError,
    _EVIDENCE_REF_KIND_TABLE,
)


CONTENT_SCHEMA_ID = "layer3.analysis_product_content.v1"
_CONTENT_EVIDENCE_REFS_MAX = 200


def build_analysis_product_content(
    db: Session,
    *,
    session_id: str,
    analysis_product_id: str,
) -> dict[str, Any]:
    """Return exact stored text without writes, including incidental autoflush.

    The evidence total counts only links owned by the selected product/session.
    At most 200 links, ordered by evidence_link_id, are returned. Every returned
    target must exist in the same session; otherwise the entire read fails 409.
    References beyond the cap are counted but are not loaded or validated.
    Oversized stored text fails closed rather than silently truncating prose.
    Missing products return 404; products in another session return 409, as in
    the existing lineage reader.
    """
    with db.no_autoflush:
        product = (
            db.query(
                L3AnalysisProduct.analysis_product_id,
                L3AnalysisProduct.title,
                L3AnalysisProduct.body,
                L3AnalysisProduct.product_kind,
                L3AnalysisProduct.executor_type,
                L3AnalysisProduct.lifecycle_status,
                L3AnalysisProduct.is_non_evidentiary,
                L3AnalysisProduct.basis_hash,
                L3AnalysisProduct.spec_hash,
                L3AnalysisProduct.created_at,
            )
            .filter(
                L3AnalysisProduct.analysis_product_id == analysis_product_id,
                L3AnalysisProduct.session_id == session_id,
            )
            .one_or_none()
        )
        if product is None:
            exists_elsewhere = (
                db.query(L3AnalysisProduct.analysis_product_id)
                .filter(L3AnalysisProduct.analysis_product_id == analysis_product_id)
                .first()
            )
            if exists_elsewhere is not None:
                raise Layer3AnalysisProductError(
                    f"analysis_product_id '{analysis_product_id}' exists but does not belong to session '{session_id}'.",
                    error_code="analysis_product_not_in_session",
                    http_status=409,
                )
            raise Layer3AnalysisProductError(
                f"analysis_product_id '{analysis_product_id}' not found.",
                error_code="analysis_product_not_found",
                http_status=404,
            )

        # Match the existing authoring limits, preserving admitted text exactly.
        if len(product.title) > 256 or len(product.body) > 16384:
            raise Layer3AnalysisProductError(
                "Stored analysis product text exceeds the supported authoring limits.",
                error_code="analysis_product_content_exceeds_limit",
                http_status=409,
            )

        links_query = db.query(
            L3AnalysisProductEvidenceLink.ref_kind,
            L3AnalysisProductEvidenceLink.ref_id,
            L3AnalysisProductEvidenceLink.evidence_role,
        ).filter(
            L3AnalysisProductEvidenceLink.analysis_product_id == analysis_product_id,
            L3AnalysisProductEvidenceLink.session_id == session_id,
        )
        evidence_refs_total = links_query.count()
        links = (
            links_query.order_by(L3AnalysisProductEvidenceLink.evidence_link_id.asc())
            .limit(_CONTENT_EVIDENCE_REFS_MAX)
            .all()
        )

        # Reuse the author's canonical kind mapping, selecting only target IDs.
        # Grouping bounds validation to one query per admitted reference kind.
        refs_by_kind: dict[str, set[str]] = {}
        for link in links:
            refs_by_kind.setdefault(link.ref_kind, set()).add(link.ref_id)
        for ref_kind, ref_ids in refs_by_kind.items():
            target = _EVIDENCE_REF_KIND_TABLE.get(ref_kind)
            found_ids: set[str] = set()
            if target is not None:
                model_cls, pk_attr = target
                pk_col = getattr(model_cls, pk_attr)
                found_ids = {
                    row[0]
                    for row in db.query(pk_col)
                    .filter(pk_col.in_(sorted(ref_ids)), model_cls.session_id == session_id)
                    .all()
                }
            if found_ids != ref_ids:
                raise Layer3AnalysisProductError(
                    "Selected analysis product evidence is not available in this session.",
                    error_code="evidence_ref_not_found_in_session",
                    http_status=409,
                )

        return {
            "schema_id": CONTENT_SCHEMA_ID,
            "session_id": session_id,
            "analysis_product": {
                "analysis_product_id": product.analysis_product_id,
                "title": product.title,
                "body": product.body,
                "product_kind": product.product_kind,
                "executor_type": product.executor_type,
                "lifecycle_status": product.lifecycle_status,
                "is_non_evidentiary": bool(product.is_non_evidentiary),
                "basis_hash": product.basis_hash,
                "spec_hash": product.spec_hash,
                "created_at": product.created_at.isoformat() if product.created_at is not None else None,
            },
            "evidence_refs": [
                {"ref_kind": link.ref_kind, "ref_id": link.ref_id, "evidence_role": link.evidence_role}
                for link in links
            ],
            "evidence_refs_total": evidence_refs_total,
            "evidence_refs_truncated": evidence_refs_total > _CONTENT_EVIDENCE_REFS_MAX,
        }
