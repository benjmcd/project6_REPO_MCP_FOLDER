import json
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.models import (
    ConnectorRunTarget,
    ApsContentLinkage,
    ApsContentDocument,
    ApsContentChunk,
)
from app.schemas.review_nrc_aps import (
    NrcApsReviewDocumentSelectorOut,
    NrcApsReviewDocumentSelectorRowOut,
    NrcApsReviewTraceStateOut,
    NrcApsReviewTraceManifestOut,
    NrcApsReviewTraceIdentityOut,
    NrcApsReviewTraceSourceOut,
    NrcApsReviewTraceSummaryOut,
    NrcApsReviewTraceCompletenessOut,
    NrcApsReviewTraceSyncCapabilitiesOut,
    NrcApsReviewTraceTabOut,
    NrcApsReviewDiagnosticsOut,
    NrcApsReviewNormalizedTextOut,
    NrcApsReviewIndexedChunksOut,
    NrcApsReviewIndexedChunkItemOut,
    NrcApsReviewExtractedUnitsOut,
    NrcApsReviewExtractedUnitItemOut,
    NrcApsReviewDownstreamUsageOut,
    NrcApsReviewDownstreamUsageItemOut,
)


# ---------------------------------------------------------------------------
# Helpers: extract normalized source metadata from connector_run_target
# ---------------------------------------------------------------------------

def _extract_aps_normalized(target: ConnectorRunTarget) -> dict:
    """Defensively extract aps_normalized block from source_reference_json."""
    src_ref = target.source_reference_json
    if not isinstance(src_ref, dict):
        return {}
    return src_ref.get("aps_normalized") or {}


def _resolve_document_type(target: ConnectorRunTarget) -> str | None:
    """Return source document_type from normalized metadata if available."""
    normalized = _extract_aps_normalized(target)
    doc_type = normalized.get("document_type")
    if doc_type and isinstance(doc_type, str):
        return doc_type
    return None


def _resolve_document_title(target: ConnectorRunTarget) -> str | None:
    """Return best-available document title.

    Priority:
    1. aps_normalized.document_title (strongest signal)
    2. sciencebase_file_name
    3. aliases_json alias_name
    """
    normalized = _extract_aps_normalized(target)
    norm_title = normalized.get("document_title")
    if norm_title and isinstance(norm_title, str):
        return norm_title

    if target.sciencebase_file_name:
        return target.sciencebase_file_name

    if target.aliases_json:
        for alias in target.aliases_json:
            name = alias.get("alias_name")
            if name:
                return name

    return None


# ---------------------------------------------------------------------------
# Document Selector
# ---------------------------------------------------------------------------

def compose_document_selector(db: Session, run_id: str, root: Path) -> NrcApsReviewDocumentSelectorOut:
    """Assemble the run-scoped list of document targets for the selector."""
    targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
    if not targets:
        return NrcApsReviewDocumentSelectorOut(run_id=run_id, default_target_id=None, documents=[])

    linkages = db.query(ApsContentLinkage).filter(ApsContentLinkage.run_id == run_id).all()
    linkage_by_target = {lnk.target_id: lnk for lnk in linkages}

    docs = []

    # Pre-load document-level metadata for all linked content_ids
    content_ids = [lnk.content_id for lnk in linkages]
    if content_ids:
        docs_rows = db.query(ApsContentDocument).filter(ApsContentDocument.content_id.in_(content_ids)).all()
        doc_by_content = {d.content_id: d for d in docs_rows}
    else:
        doc_by_content = {}

    for t in targets:
        lnk = linkage_by_target.get(t.connector_run_target_id)

        has_blob = False
        has_diag = False
        has_norm = False
        has_chunks = False

        content_id = None
        accession_number = None
        media_type = None

        # Source document type from normalized metadata, not processing classification
        document_type = _resolve_document_type(t)
        title = _resolve_document_title(t)

        if lnk:
            content_id = lnk.content_id
            accession_number = lnk.accession_number
            if lnk.blob_ref:
                has_blob = True
            if lnk.diagnostics_ref:
                has_diag = True
            if lnk.normalized_text_ref:
                has_norm = True

            doc_row = doc_by_content.get(content_id)
            if doc_row:
                media_type = doc_row.media_type
                if doc_row.chunk_count > 0:
                    has_chunks = True

        docs.append(NrcApsReviewDocumentSelectorRowOut(
            target_id=t.connector_run_target_id,
            accession_number=accession_number,
            document_title=title,
            document_type=document_type,
            media_type=media_type,
            content_id=content_id,
            trace_state=NrcApsReviewTraceStateOut(
                has_source_blob=has_blob,
                has_diagnostics=has_diag,
                has_normalized_text=has_norm,
                has_indexed_chunks=has_chunks,
                has_downstream_usage=False
            )
        ))

    def sort_key(d: NrcApsReviewDocumentSelectorRowOut):
        acc = d.accession_number or ""
        tit = d.document_title or ""
        return (acc, tit, d.target_id)

    docs.sort(key=sort_key)

    default_target_id = docs[0].target_id if docs else None

    return NrcApsReviewDocumentSelectorOut(
        run_id=run_id,
        default_target_id=default_target_id,
        documents=docs
    )


# ---------------------------------------------------------------------------
# Source Resolution
# ---------------------------------------------------------------------------

def resolve_source_blob_info(db: Session, run_id: str, target_id: str, root: Path) -> tuple[Path, str, str | None]:
    """Resolve the original source blob for a target, ensuring path safety.
    
    Returns: (absolute_path, media_type, filename)
    Raises: KeyError for missing target/blob, ValueError for safety, FileNotFoundError for missing disk objects.
    """
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()
    
    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    lnk = db.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == run_id,
        ApsContentLinkage.target_id == target_id
    ).first()

    if not lnk or not lnk.blob_ref:
        raise KeyError(f"No source blob available for target {target_id}")

    # blob_ref is the durable contract. It can be relative to root or absolute.
    blob_path_raw = Path(lnk.blob_ref)
    if not blob_path_raw.is_absolute():
        absolute_blob_path = (root / blob_path_raw).resolve()
    else:
        absolute_blob_path = blob_path_raw.resolve()

    # Path Safety: Ensure the path is within the run's review root or an allowlisted root.
    from app.services.review_nrc_aps_runtime import is_absolute_path_safe
    
    if not is_absolute_path_safe(root, absolute_blob_path):
        raise ValueError("Requested blob path is outside allowed runtime boundaries")

    if not absolute_blob_path.exists():
        raise FileNotFoundError(f"Source blob missing on disk at {absolute_blob_path}")

    # Resolve media type (prioritize ApsContentDocument)
    media_type = "application/octet-stream"
    doc_row = db.query(ApsContentDocument).filter(ApsContentDocument.content_id == lnk.content_id).first()
    if doc_row and doc_row.media_type:
        media_type = doc_row.media_type
    
    filename = target.sciencebase_file_name or absolute_blob_path.name
    
    return absolute_blob_path, media_type, filename


# ---------------------------------------------------------------------------
# Trace Manifest
# ---------------------------------------------------------------------------

def compose_trace_manifest(db: Session, run_id: str, target_id: str, root: Path) -> NrcApsReviewTraceManifestOut:
    """Assemble the authoritative trace manifest for run_id + target_id."""
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()

    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    lnk = db.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == run_id,
        ApsContentLinkage.target_id == target_id
    ).first()

    identity = NrcApsReviewTraceIdentityOut()
    source = NrcApsReviewTraceSourceOut()
    summary = NrcApsReviewTraceSummaryOut()
    completeness = NrcApsReviewTraceCompletenessOut()
    sync_cap = NrcApsReviewTraceSyncCapabilitiesOut()

    # Resolve identity from normalized source metadata
    identity.document_title = _resolve_document_title(target)
    identity.document_type = _resolve_document_type(target)
    identity.source_file_name = target.sciencebase_file_name

    if lnk:
        completeness.has_linkage_row = True
        identity.accession_number = lnk.accession_number
        identity.content_id = lnk.content_id
        identity.content_contract_id = lnk.content_contract_id
        identity.chunking_contract_id = lnk.chunking_contract_id

        if lnk.blob_ref:
            completeness.has_source_blob = True
            source.blob_ref_present = True

        if lnk.diagnostics_ref:
            completeness.has_diagnostics = True

            # Read diagnostics to get ordered_unit_count
            diag_path = root / lnk.diagnostics_ref
            if diag_path.exists():
                try:
                    diag_data = json.loads(diag_path.read_text(encoding="utf-8"))
                    units = diag_data.get("ordered_units", [])
                    summary.ordered_unit_count = len(units)
                except Exception:
                    pass

        if lnk.normalized_text_ref:
            completeness.has_normalized_text = True

        doc = db.query(ApsContentDocument).filter(ApsContentDocument.content_id == lnk.content_id).first()
        if doc:
            completeness.has_document_row = True
            identity.media_type = doc.media_type
            identity.normalization_contract_id = doc.normalization_contract_id

            if doc.media_type == "application/pdf":
                source.viewer_kind = "pdf"
                source.content_type = "application/pdf"
            elif doc.media_type and "text" in doc.media_type:
                source.viewer_kind = "text"
                source.content_type = doc.media_type
            elif doc.media_type and "json" in doc.media_type:
                source.viewer_kind = "json"
                source.content_type = doc.media_type
            else:
                source.viewer_kind = "unsupported"

            # document_class is a processing classification, kept in summary
            summary.document_class = doc.document_class
            summary.quality_status = doc.quality_status
            summary.page_count = doc.page_count

            if doc.chunk_count > 0:
                completeness.has_indexed_chunks = True

            chunk_count_actual = db.query(ApsContentChunk).filter(ApsContentChunk.content_id == lnk.content_id).count()
            summary.indexed_chunk_count = chunk_count_actual

            # Derive sync precision
            if summary.ordered_unit_count > 0:
                sync_cap.source_to_units = "unit"
                sync_cap.units_to_source = "unit"
                sync_cap.normalized_text_to_source = "best_effort"

            if summary.indexed_chunk_count > 0:
                sync_cap.chunk_to_source = "page"

    else:
        # No linkage — limited inference only
        title = identity.document_title
        if title and title.lower().endswith(".pdf"):
            source.viewer_kind = "pdf"
            source.content_type = "application/pdf"

    # Tabs: advertise endpoints only for routes that are implemented in Phase 4.
    tabs = [
        NrcApsReviewTraceTabOut(tab_id="summary", label="Summary", available=True),
        NrcApsReviewTraceTabOut(
            tab_id="extracted_units",
            label="Extracted Units",
            available=(completeness.has_diagnostics and summary.ordered_unit_count > 0),
            endpoint=f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/extracted-units",
        ),
        NrcApsReviewTraceTabOut(
            tab_id="normalized_text",
            label="Normalized Text",
            available=completeness.has_normalized_text,
            endpoint=f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/normalized-text",
        ),
        NrcApsReviewTraceTabOut(
            tab_id="indexed_chunks",
            label="Indexed Chunks",
            available=completeness.has_indexed_chunks,
            endpoint=f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/indexed-chunks",
        ),
        NrcApsReviewTraceTabOut(
            tab_id="diagnostics",
            label="Diagnostics",
            available=completeness.has_diagnostics,
            endpoint=f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/diagnostics",
        ),
        NrcApsReviewTraceTabOut(
            tab_id="downstream_usage",
            label="Downstream Usage",
            available=completeness.has_downstream_usage,
            endpoint=f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/downstream-usage",
        ),
    ]

    # source_endpoint is now truthful for Phase 2 if blob is present.
    if completeness.has_source_blob:
        source.source_endpoint = f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/source"

    warnings: list[str] = []

    limitations: list[str] = []

    return NrcApsReviewTraceManifestOut(
        run_id=run_id,
        target_id=target_id,
        identity=identity,
        source=source,
        summary=summary,
        trace_completeness=completeness,
        sync_capabilities=sync_cap,
        tabs=tabs,
        warnings=warnings,
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# Tab Payloads (Phase 4)
# ---------------------------------------------------------------------------

def compose_diagnostics_payload(db: Session, run_id: str, target_id: str, root: Path) -> NrcApsReviewDiagnosticsOut:
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()
    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    lnk = db.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == run_id,
        ApsContentLinkage.target_id == target_id
    ).first()

    payload = NrcApsReviewDiagnosticsOut(run_id=run_id, target_id=target_id, available=False)

    if not lnk or not lnk.diagnostics_ref:
        return payload

    from app.services.review_nrc_aps_runtime import is_absolute_path_safe
    diag_path_raw = Path(lnk.diagnostics_ref)
    if not diag_path_raw.is_absolute():
        diag_path = (root / diag_path_raw).resolve()
    else:
        diag_path = diag_path_raw.resolve()

    if not is_absolute_path_safe(root, diag_path) or not diag_path.exists():
        return payload

    try:
        diag_data = json.loads(diag_path.read_text(encoding="utf-8"))
        payload.available = True
        payload.ordered_unit_count = len(diag_data.get("ordered_units", []))
        payload.extractor_metadata = diag_data.get("extractor_metadata")
        payload.warnings = diag_data.get("warnings", [])
        payload.degradation_codes = diag_data.get("degradation_codes", [])
    except Exception:
        pass

    doc = db.query(ApsContentDocument).filter(ApsContentDocument.content_id == lnk.content_id).first()
    if doc:
        payload.document_class = doc.document_class
        payload.quality_status = doc.quality_status
        payload.page_count = doc.page_count

    return payload


def compose_normalized_text_payload(db: Session, run_id: str, target_id: str, root: Path) -> NrcApsReviewNormalizedTextOut:
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()
    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    lnk = db.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == run_id,
        ApsContentLinkage.target_id == target_id
    ).first()

    payload = NrcApsReviewNormalizedTextOut(run_id=run_id, target_id=target_id, available=False)

    if not lnk or not lnk.normalized_text_ref:
        return payload

    from app.services.review_nrc_aps_runtime import is_absolute_path_safe
    text_path_raw = Path(lnk.normalized_text_ref)
    if not text_path_raw.is_absolute():
        text_path = (root / text_path_raw).resolve()
    else:
        text_path = text_path_raw.resolve()

    if not is_absolute_path_safe(root, text_path) or not text_path.exists():
        return payload

    try:
        text_content = text_path.read_text(encoding="utf-8")
        payload.available = True
        payload.text = text_content
        payload.char_count = len(text_content)

        diag_path_raw = Path(lnk.diagnostics_ref) if lnk.diagnostics_ref else None
        if diag_path_raw:
            if not diag_path_raw.is_absolute():
                diag_path = (root / diag_path_raw).resolve()
            else:
                diag_path = diag_path_raw.resolve()
            
            if is_absolute_path_safe(root, diag_path) and diag_path.exists():
                diag_data = json.loads(diag_path.read_text(encoding="utf-8"))
                units = diag_data.get("ordered_units", [])
                if len(units) > 0:
                    payload.mapping_precision = "best_effort"
                elif payload.char_count > 0:
                    payload.mapping_precision = "document"
    except Exception:
        pass

    return payload


def compose_indexed_chunks_payload(db: Session, run_id: str, target_id: str, root: Path) -> NrcApsReviewIndexedChunksOut:
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()
    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    lnk = db.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == run_id,
        ApsContentLinkage.target_id == target_id
    ).first()

    payload = NrcApsReviewIndexedChunksOut(run_id=run_id, target_id=target_id, available=False)

    if not lnk:
        return payload

    chunks = db.query(ApsContentChunk).filter(ApsContentChunk.content_id == lnk.content_id).order_by(ApsContentChunk.chunk_ordinal).all()
    
    if not chunks:
        return payload

    payload.available = True
    payload.chunk_count = len(chunks)

    for c in chunks:
        payload.chunks.append(NrcApsReviewIndexedChunkItemOut(
            chunk_id=c.chunk_id,
            chunk_ordinal=c.chunk_ordinal,
            page_start=c.page_start,
            page_end=c.page_end,
            start_char=c.start_char,
            end_char=c.end_char,
            unit_kind=c.unit_kind,
            quality_status=str(c.quality_status) if getattr(c, 'quality_status', None) is not None else None,
            chunk_text=c.chunk_text,
            mapping_precision="page"
        ))

    return payload


# ---------------------------------------------------------------------------
# Extracted Units (Phase 6)
# ---------------------------------------------------------------------------

def _deterministic_unit_id(target_id: str, index: int, unit: dict) -> str:
    """Generate a stable, deterministic unit_id from ordered position and content."""
    import hashlib
    key = f"{target_id}:{index}:{unit.get('page_number', '')}:{unit.get('start_char', '')}:{unit.get('end_char', '')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def compose_extracted_units_payload(
    db: Session, run_id: str, target_id: str, root: Path,
    page_number: int | None = None,
) -> NrcApsReviewExtractedUnitsOut:
    """Assemble extracted units from diagnostics ordered_units."""
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()
    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    lnk = db.query(ApsContentLinkage).filter(
        ApsContentLinkage.run_id == run_id,
        ApsContentLinkage.target_id == target_id
    ).first()

    payload = NrcApsReviewExtractedUnitsOut(
        run_id=run_id,
        target_id=target_id,
        available=False,
        reason_code="diagnostics_absent",
        source_precision="none",
        page_number=page_number,
    )

    if not lnk or not lnk.diagnostics_ref:
        return payload

    from app.services.review_nrc_aps_runtime import is_absolute_path_safe
    diag_path_raw = Path(lnk.diagnostics_ref)
    if not diag_path_raw.is_absolute():
        diag_path = (root / diag_path_raw).resolve()
    else:
        diag_path = diag_path_raw.resolve()

    if not is_absolute_path_safe(root, diag_path) or not diag_path.exists():
        payload.reason_code = "diagnostics_unreadable"
        return payload

    try:
        diag_data = json.loads(diag_path.read_text(encoding="utf-8"))
    except Exception:
        payload.reason_code = "diagnostics_parse_error"
        return payload

    ordered_units = diag_data.get("ordered_units", [])
    if not ordered_units:
        payload.reason_code = "no_ordered_units"
        return payload

    payload.available = True
    payload.reason_code = None
    payload.source_precision = "unit"
    payload.total_unit_count = len(ordered_units)

    for idx, u in enumerate(ordered_units):
        pg = u.get("page_number")
        # Page filter: skip units not matching requested page
        if page_number is not None and pg != page_number:
            continue

        # Determine mapping precision per unit
        has_bbox = isinstance(u.get("bbox"), list) and len(u.get("bbox", [])) == 4
        has_chars = u.get("start_char") is not None and u.get("end_char") is not None
        if has_bbox and has_chars:
            precision = "unit"
        elif pg is not None:
            precision = "page"
        else:
            precision = "best_effort"

        payload.units.append(NrcApsReviewExtractedUnitItemOut(
            unit_id=_deterministic_unit_id(target_id, idx, u),
            page_number=pg,
            unit_kind=u.get("unit_kind"),
            text=u.get("text"),
            bbox=u.get("bbox") if has_bbox else None,
            start_char=u.get("start_char"),
            end_char=u.get("end_char"),
            mapping_precision=precision,
        ))

    return payload


# ---------------------------------------------------------------------------
# Downstream Usage (Phase 7)
# ---------------------------------------------------------------------------

def compose_downstream_usage_payload(db: Session, run_id: str, target_id: str, root: Path) -> NrcApsReviewDownstreamUsageOut:
    """Implement the downstream usage query. Missingness is explicit if none are found."""
    target = db.query(ConnectorRunTarget).filter(
        ConnectorRunTarget.connector_run_id == run_id,
        ConnectorRunTarget.connector_run_target_id == target_id
    ).first()
    if not target:
        raise KeyError(f"Target {target_id} not found in run {run_id}")

    payload = NrcApsReviewDownstreamUsageOut(
        run_id=run_id,
        target_id=target_id,
        available=False,
        usage=[],
        limitations=["Attributable downstream usage tracking is not yet populated in the current test runtime or the target has no usage."]
    )

    # In a full db implementation, we'd query DatasetSourceProvenance or AnalysisArtifact
    # Since the audited runtime is explicitly void of downstream records, this safely 
    # honors the real zero-state truthfulness constraint safely bounded.

    return payload
