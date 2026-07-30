"""Strict downstream linkage for one admitted NRC APS raw target."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
)
from app.services import connector_egress_arming
from app.services import connectors_nrc_adams
from app.services import layer3_origin_continuity
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_content_index
from app.services import nrc_aps_strict_parse
from app.services.raw_storage_handles import (
    StableRawStorageError,
    hash_locked_raw_file,
    locked_raw_file_snapshot,
)


_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ACCESSION = connectors_nrc_adams.NRC_FRESH_ACCESSION
_ORIGIN_RECEIPT_KEY = (
    layer3_origin_continuity.ORIGIN_RECEIPT_STORAGE_KEY
)
_ADMISSION_KEYS = frozenset(
    {
        "schema_id",
        "accession_number",
        "artifact_file_name",
        "detail_response_sha256",
        "artifact_url_sha256",
        "artifact_path_class",
        "raw_content_sha256",
        "raw_content_size_bytes",
        "media_type",
        "blob_storage_layout",
    }
)
_ADMISSION_KEY_SETS = frozenset(
    {
        _ADMISSION_KEYS,
        _ADMISSION_KEYS | {_ORIGIN_RECEIPT_KEY},
    }
)


class NrcPhaseBLinkageError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> None:
    raise NrcPhaseBLinkageError(code, message)


def _text(value: object) -> str:
    return str(value or "").strip()


def _sha256(value: object, *, field: str) -> str:
    digest = _text(value)
    if not _SHA256_RE.fullmatch(digest):
        _fail(
            "nrc_phase_b_admission_invalid",
            f"{field} is not a lowercase SHA-256.",
        )
    return digest


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _same_lexical_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(
        os.path.normpath(str(right))
    )


def _contains_url(value: object) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return (
            normalized.startswith("http://")
            or normalized.startswith("https://")
            or normalized.startswith("//")
        )
    if isinstance(value, Mapping):
        return any(_contains_url(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_url(item) for item in value)
    return False


def _require_owned_clean_transaction(db: Session) -> None:
    if (
        db.in_transaction()
        or db.in_nested_transaction()
        or db.new
        or db.dirty
        or db.deleted
    ):
        _fail(
            "nrc_phase_b_transaction_not_owned",
            "Phase B requires a clean Session with no active transaction.",
        )


def _validate_run(db: Session, run: ConnectorRun) -> None:
    if (
        run.connector_key != "nrc_adams_aps"
        or run.source_system != "nrc_adams_aps"
        or run.source_mode != "strict_live_egress"
        or run.status != "completed"
        or not connector_egress_arming.is_strict_egress_run(run)
        or run.discovered_count != 1
        or run.selected_count != 1
        or run.downloaded_count != 1
        or run.ingested_count != 0
        or run.failed_count != 0
        or run.terminal_target_count != 1
        or run.nonterminal_target_count != 0
        or run.consumed_bytes <= 0
    ):
        _fail(
            "nrc_phase_b_run_invalid",
            "Target parent is not one completed strict NRC raw-only run.",
        )
    events = (
        db.query(ConnectorRunEvent)
        .filter(
            ConnectorRunEvent.connector_run_id
            == run.connector_run_id
        )
        .all()
    )
    try:
        connector_egress_arming._assert_nrc_terminal_transition(
            run,
            events=events,
            now=datetime.now(timezone.utc),
        )
    except connector_egress_arming.ConnectorEgressArmingError as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_run_invalid",
            "Strict NRC terminal transition is not structurally valid.",
        ) from exc


def _validate_target(
    target: ConnectorRunTarget,
    *,
    run: ConnectorRun,
) -> tuple[str, int]:
    if (
        target.connector_run_id != run.connector_run_id
        or target.ordinal != 1
        or target.stable_release_key != _ACCESSION
        or target.stable_release_identifier
        != f"adams_accession:{_ACCESSION}"
        or target.identifiers_json
        != [{"type": "AccessionNumber", "value": _ACCESSION}]
        or target.sciencebase_item_id is not None
        or target.sciencebase_file_name
        != connectors_nrc_adams.NRC_FRESH_FILENAME
        or target.artifact_surface != "files"
        or target.selection_source != "strict_exact_accession"
        or target.selection_scope != "dual_live_proof_v1"
        or target.selection_match_basis != "exact_accession"
        or target.artifact_locator_type
        != connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
        or target.source_artifact_key
        != f"nrc_adams_aps::{_ACCESSION}"
        or target.canonical_artifact_key
        != f"nrc_adams_aps::{_ACCESSION}"
        or target.fetch_policy_mode != "strict_live_egress"
        or target.redirect_count != 0
        or target.aliases_json != []
        or target.permission_snapshot_json
        != {"direct_public_200": True}
        or target.access_level_summary != "public_direct_200"
        or target.public_read_confirmed is not True
        or target.status != "downloaded"
        or target.retry_eligible is not False
        or target.attempt_count != 1
        or target.ingested_at is not None
        or target.profiled_at is not None
        or target.recommended_at is not None
    ):
        _fail(
            "nrc_phase_b_target_invalid",
            "Run target is not the canonical ordinal-1 NRC raw target.",
        )
    if (
        target.sciencebase_item_url is not None
        or target.sciencebase_download_uri is not None
        or _contains_url(target.aliases_json)
    ):
        _fail(
            "nrc_phase_b_url_authority_refused",
            "URL-bearing target authority is forbidden in Phase B.",
        )

    admission = target.source_reference_json
    if (
        not isinstance(admission, Mapping)
        or frozenset(admission) not in _ADMISSION_KEY_SETS
        or admission.get("schema_id")
        != "project6.nrc_raw_admission.v1"
        or admission.get("accession_number") != _ACCESSION
        or admission.get("artifact_file_name")
        != connectors_nrc_adams.NRC_FRESH_FILENAME
        or admission.get("artifact_path_class")
        != connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
        or admission.get("media_type")
        not in connectors_nrc_adams.NRC_FRESH_MEDIA_TYPES
        or admission.get("blob_storage_layout")
        != "nrc_aps_blob_sha256_v1"
        or _contains_url(admission)
    ):
        _fail(
            "nrc_phase_b_admission_invalid",
            "Target lacks exact URL-free NRC raw admission metadata.",
        )
    receipt = admission.get(_ORIGIN_RECEIPT_KEY)
    if _ORIGIN_RECEIPT_KEY in admission:
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("schema_id")
            != layer3_origin_continuity.ORIGIN_RECEIPT_SCHEMA_ID
            or receipt.get("connector_key") != run.connector_key
            or receipt.get("connector_run_id")
            != run.connector_run_id
            or receipt.get("connector_run_target_id")
            != target.connector_run_target_id
        ):
            _fail(
                "nrc_phase_b_admission_invalid",
                "Optional connector-origin receipt envelope is invalid.",
            )
        _sha256(
            receipt.get("receipt_hash"),
            field="connector_origin_receipt_v1.receipt_hash",
        )
    _sha256(
        admission.get("detail_response_sha256"),
        field="detail_response_sha256",
    )
    _sha256(
        admission.get("artifact_url_sha256"),
        field="artifact_url_sha256",
    )
    raw_sha256 = _sha256(
        admission.get("raw_content_sha256"),
        field="raw_content_sha256",
    )
    target_sha256 = _sha256(
        target.downloaded_sha256,
        field="ConnectorRunTarget.downloaded_sha256",
    )
    raw_size = admission.get("raw_content_size_bytes")
    if (
        isinstance(raw_size, bool)
        or not isinstance(raw_size, int)
        or raw_size <= 0
        or raw_size > connectors_nrc_adams.NRC_FRESH_MAX_PDF_BYTES
        or raw_size != run.consumed_bytes
        or raw_sha256 != target_sha256
        or not _text(target.raw_storage_ref)
    ):
        _fail(
            "nrc_phase_b_admission_invalid",
            "Raw admission size, hash, or storage binding is invalid.",
        )
    return raw_sha256, raw_size


def _safe_rehash(
    target: ConnectorRunTarget,
    *,
    expected_sha256: str,
    expected_size: int,
    drift_phase: bool,
) -> Path:
    raw_root = _lexical_absolute(Path(settings.connector_raw_dir))
    expected_path = _lexical_absolute(
        raw_root
        / nrc_aps_artifact_ingestion.blob_relative_path(
            sha256=expected_sha256
        )
    )
    raw_ref = target.raw_storage_ref
    if (
        not isinstance(raw_ref, str)
        or not raw_ref
        or raw_ref != raw_ref.strip()
    ):
        _fail(
            "nrc_phase_b_raw_path_invalid",
            "Raw storage ref is not one canonical absolute string.",
        )
    target_path = _lexical_absolute(Path(raw_ref))
    if not _same_lexical_path(target_path, expected_path):
        _fail(
            "nrc_phase_b_raw_path_invalid",
            "Raw storage ref is not the exact content-addressed path.",
        )
    try:
        size, digest, resolved_ref = hash_locked_raw_file(
            raw_root,
            expected_path,
        )
    except StableRawStorageError as exc:
        code = (
            "nrc_phase_b_raw_drift"
            if drift_phase
            else "nrc_phase_b_raw_storage_unsafe"
        )
        raise NrcPhaseBLinkageError(
            code,
            "Handle-safe raw storage validation failed closed.",
        ) from exc
    resolved_path = _lexical_absolute(Path(resolved_ref))
    if (
        not _same_lexical_path(resolved_path, expected_path)
        or raw_ref != resolved_ref
        or size != expected_size
        or digest != expected_sha256
    ):
        if raw_ref != resolved_ref:
            _fail(
                "nrc_phase_b_raw_path_invalid",
                "Raw storage ref is not the canonical locked reference.",
            )
        code = (
            "nrc_phase_b_raw_drift"
            if drift_phase
            else "nrc_phase_b_raw_binding_mismatch"
        )
        _fail(code, "Rehashed raw bytes contradict admission authority.")
    return resolved_path


def _run_snapshot(run: ConnectorRun) -> tuple[Any, ...]:
    return (
        run.connector_run_id,
        run.connector_key,
        run.source_system,
        run.source_mode,
        run.status,
        json.dumps(run.request_config_json, sort_keys=True),
        run.submission_idempotency_key,
        run.completed_at,
        run.discovered_count,
        run.selected_count,
        run.downloaded_count,
        run.ingested_count,
        run.consumed_bytes,
        run.failed_count,
        run.terminal_target_count,
        run.nonterminal_target_count,
        run.execution_lease_owner,
        run.execution_lease_token,
        run.execution_lease_expires_at,
        run.error_summary,
    )


def _target_snapshot(target: ConnectorRunTarget) -> tuple[Any, ...]:
    return (
        target.connector_run_target_id,
        target.connector_run_id,
        target.ordinal,
        target.stable_release_key,
        target.stable_release_identifier,
        json.dumps(target.identifiers_json, sort_keys=True),
        target.sciencebase_item_id,
        target.sciencebase_item_url,
        target.sciencebase_file_name,
        target.sciencebase_download_uri,
        target.artifact_surface,
        target.selection_source,
        target.selection_scope,
        target.selection_match_basis,
        target.artifact_locator_type,
        target.source_artifact_key,
        target.canonical_artifact_key,
        target.downloaded_sha256,
        target.raw_storage_ref,
        target.fetch_policy_mode,
        target.redirect_count,
        json.dumps(target.aliases_json, sort_keys=True),
        json.dumps(target.source_reference_json, sort_keys=True),
        json.dumps(target.permission_snapshot_json, sort_keys=True),
        target.access_level_summary,
        target.public_read_confirmed,
        target.status,
        target.retry_eligible,
        target.attempt_count,
        target.downloaded_at,
        target.ingested_at,
        target.profiled_at,
        target.recommended_at,
        target.last_attempt_at,
        target.last_stage_transition_at,
    )


def _visual_refs(raw: str | None) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, list) or any(
        not isinstance(item, dict) for item in parsed
    ):
        return None
    return [dict(item) for item in parsed]


def _document_matches(
    document: ApsContentDocument,
    payload: Mapping[str, Any],
) -> bool:
    return bool(
        document.content_id == payload["content_id"]
        and document.content_contract_id
        == payload["content_contract_id"]
        and document.chunking_contract_id
        == payload["chunking_contract_id"]
        and document.normalization_contract_id
        == payload["normalization_contract_id"]
        and document.normalized_text_sha256
        == payload["normalized_text_sha256"]
        and document.normalized_char_count
        == payload["normalized_char_count"]
        and document.chunk_count == payload["chunk_count"]
        and document.content_status == payload["content_status"]
        and document.media_type == payload["effective_content_type"]
        and document.document_class == payload["document_class"]
        and document.quality_status == payload["quality_status"]
        and document.page_count == payload["page_count"]
        and document.diagnostics_ref is None
        and _visual_refs(document.visual_page_refs_json) == []
    )


def _chunks_match(
    rows: list[ApsContentChunk],
    payload: Mapping[str, Any],
) -> bool:
    expected_rows = payload.get("chunks")
    if not isinstance(expected_rows, list) or len(rows) != len(expected_rows):
        return False
    by_id = {row.chunk_id: row for row in rows}
    if len(by_id) != len(rows):
        return False
    for raw_expected in expected_rows:
        if not isinstance(raw_expected, Mapping):
            return False
        expected = dict(raw_expected)
        row = by_id.get(expected.get("chunk_id"))
        if row is None or not (
            row.content_id == payload["content_id"]
            and row.content_contract_id
            == payload["content_contract_id"]
            and row.chunking_contract_id
            == payload["chunking_contract_id"]
            and row.chunk_ordinal == expected.get("chunk_ordinal")
            and row.start_char == expected.get("start_char")
            and row.end_char == expected.get("end_char")
            and row.chunk_text == expected.get("chunk_text")
            and row.chunk_text_sha256
            == expected.get("chunk_text_sha256")
            and row.page_start == expected.get("page_start")
            and row.page_end == expected.get("page_end")
            and row.unit_kind == expected.get("unit_kind")
            and row.quality_status == payload["quality_status"]
        ):
            return False
    return True


def _linkage_matches(
    linkage: ApsContentLinkage,
    payload: Mapping[str, Any],
) -> bool:
    return bool(
        linkage.content_id == payload["content_id"]
        and linkage.run_id == payload["run_id"]
        and linkage.target_id == payload["target_id"]
        and linkage.accession_number == payload["accession_number"]
        and linkage.content_contract_id
        == payload["content_contract_id"]
        and linkage.chunking_contract_id
        == payload["chunking_contract_id"]
        and linkage.content_units_ref is None
        and linkage.normalized_text_ref is None
        and linkage.normalized_text_sha256
        == payload["normalized_text_sha256"]
        and linkage.blob_ref == payload["blob_ref"]
        and linkage.blob_sha256 == payload["blob_sha256"]
        and linkage.download_exchange_ref is None
        and linkage.discovery_ref is None
        and linkage.selection_ref is None
        and linkage.diagnostics_ref is None
    )


def _content_projection(
    db: Session,
    payload: Mapping[str, Any],
) -> tuple[list[ApsContentDocument], list[ApsContentChunk]]:
    documents = (
        db.query(ApsContentDocument)
        .filter(
            ApsContentDocument.content_id == payload["content_id"]
        )
        .with_for_update()
        .all()
    )
    chunks = (
        db.query(ApsContentChunk)
        .filter(ApsContentChunk.content_id == payload["content_id"])
        .with_for_update()
        .all()
    )
    return documents, chunks


def _preflight(
    db: Session,
    *,
    payload: Mapping[str, Any],
) -> tuple[str, ApsContentLinkage | None]:
    linkages = (
        db.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == payload["run_id"],
            ApsContentLinkage.target_id == payload["target_id"],
        )
        .with_for_update()
        .all()
    )
    if len(linkages) > 1:
        _fail(
            "nrc_phase_b_linkage_cardinality",
            "Run-target pair already has more than one linkage.",
        )
    documents, chunks = _content_projection(db, payload)
    if len(linkages) == 1:
        linkage = linkages[0]
        if not _linkage_matches(linkage, payload):
            _fail(
                "nrc_phase_b_linkage_mismatch",
                "Existing run-target linkage is not exact.",
            )
        if (
            len(documents) != 1
            or not _document_matches(documents[0], payload)
            or not _chunks_match(chunks, payload)
        ):
            _fail(
                "nrc_phase_b_linkage_mismatch",
                "Existing linkage document/chunk projection is not exact.",
            )
        return "existing", linkage

    if not documents and not chunks:
        return "immutable_insert", None
    if (
        len(documents) == 1
        and _document_matches(documents[0], payload)
        and _chunks_match(chunks, payload)
    ):
        return "linkage_only", None
    _fail(
        "nrc_phase_b_shared_content_mismatch",
        "Shared content state is not the exact strict projection.",
    )


def _require_exact_persisted(
    db: Session,
    *,
    payload: Mapping[str, Any],
) -> ApsContentLinkage:
    linkages = (
        db.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == payload["run_id"],
            ApsContentLinkage.target_id == payload["target_id"],
        )
        .all()
    )
    documents, chunks = _content_projection(db, payload)
    if (
        len(linkages) != 1
        or not _linkage_matches(linkages[0], payload)
        or len(documents) != 1
        or not _document_matches(documents[0], payload)
        or not _chunks_match(chunks, payload)
    ):
        _fail(
            "nrc_phase_b_persistence_conflict",
            "Committed or concurrent persistence is not exact.",
        )
    return linkages[0]


def _reload_authority(
    db: Session,
    *,
    run_id: str,
    target_id: str,
    run_snapshot: tuple[Any, ...],
    target_snapshot: tuple[Any, ...],
) -> tuple[ConnectorRun, ConnectorRunTarget]:
    run = (
        db.query(ConnectorRun)
        .filter(ConnectorRun.connector_run_id == run_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    target = (
        db.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if (
        run is None
        or target is None
        or _run_snapshot(run) != run_snapshot
        or _target_snapshot(target) != target_snapshot
    ):
        _fail(
            "nrc_phase_b_row_drift",
            "Run or target authority changed during strict parsing.",
        )
    targets = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == run_id)
        .with_for_update()
        .all()
    )
    if (
        len(targets) != 1
        or targets[0].connector_run_target_id != target_id
    ):
        _fail(
            "nrc_phase_b_row_drift",
            "Run target cardinality changed during strict parsing.",
        )
    _validate_run(db, run)
    _validate_target(target, run=run)
    return run, target


def _strict_payload(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
    blob_ref: str,
    processed: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return (
            nrc_aps_content_index
            .build_strict_content_units_payload_from_processed_output(
                run_id=run.connector_run_id,
                target_id=target.connector_run_target_id,
                accession_number=_ACCESSION,
                blob_ref=blob_ref,
                blob_sha256=raw_sha256,
                processed_output=processed,
            )
        )
    except (TypeError, ValueError) as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_parse_projection_invalid",
            "Strict parser result cannot form canonical content units.",
        ) from exc


def _bind_strict_nrc_phase_b_linkage_owned(
    db: Session,
    *,
    connector_run_target_id: str,
) -> ApsContentLinkage:
    """Bind one strict NRC Phase-B parse to server-owned raw authority."""

    target_id = _text(connector_run_target_id)
    target = db.get(ConnectorRunTarget, target_id)
    if target is None:
        _fail(
            "nrc_phase_b_target_not_found",
            "Connector run target does not exist.",
        )
    run = db.get(ConnectorRun, target.connector_run_id)
    if run is None:
        _fail(
            "nrc_phase_b_run_not_found",
            "Connector run does not exist.",
        )
    _validate_run(db, run)
    targets = (
        db.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_id
            == run.connector_run_id
        )
        .all()
    )
    if (
        len(targets) != 1
        or targets[0].connector_run_target_id != target_id
    ):
        _fail(
            "nrc_phase_b_target_cardinality",
            "Strict NRC run must have exactly one ordinal-1 target.",
        )
    raw_sha256, raw_size = _validate_target(target, run=run)
    raw_path = _safe_rehash(
        target,
        expected_sha256=raw_sha256,
        expected_size=raw_size,
        drift_phase=False,
    )
    run_authority = _run_snapshot(run)
    target_authority = _target_snapshot(target)

    try:
        processed = nrc_aps_strict_parse.parse_admitted_blob_strict(
            blob_path=raw_path,
            expected_sha256=raw_sha256,
        )
    except (
        nrc_aps_strict_parse.StrictParseViolation,
        OSError,
        ValueError,
    ) as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_parse_failed",
            "Frozen strict parser refused admitted bytes.",
        ) from exc
    payload = _strict_payload(
        run=run,
        target=target,
        raw_sha256=raw_sha256,
        blob_ref=str(raw_path),
        processed=processed,
    )

    first_action, first_existing = _preflight(db, payload=payload)
    run, target = _reload_authority(
        db,
        run_id=run.connector_run_id,
        target_id=target.connector_run_target_id,
        run_snapshot=run_authority,
        target_snapshot=target_authority,
    )
    try:
        with locked_raw_file_snapshot(
            Path(settings.connector_raw_dir),
            raw_path,
        ) as raw_snapshot:
            if (
                raw_snapshot.canonical_ref
                != target.raw_storage_ref
                or raw_snapshot.size != raw_size
                or raw_snapshot.sha256 != raw_sha256
            ):
                _fail(
                    "nrc_phase_b_raw_drift",
                    "Final locked raw snapshot contradicts admission authority.",
                )
            payload = _strict_payload(
                run=run,
                target=target,
                raw_sha256=raw_sha256,
                blob_ref=raw_snapshot.canonical_ref,
                processed=processed,
            )
            second_action, second_existing = _preflight(
                db,
                payload=payload,
            )
            if (
                first_action != second_action
                or (
                    first_existing is not None
                    and (
                        second_existing is None
                        or first_existing.aps_content_linkage_id
                        != second_existing.aps_content_linkage_id
                    )
                )
            ):
                _fail(
                    "nrc_phase_b_persistence_conflict",
                    "Persistence state changed during strict preflight.",
                )

            if second_action == "existing":
                assert second_existing is not None
                db.commit()
                return second_existing
            try:
                if second_action == "linkage_only":
                    inserted = (
                        nrc_aps_content_index
                        .insert_content_linkage_immutable(
                            db,
                            payload=payload,
                        )
                    )
                elif second_action == "immutable_insert":
                    inserted = (
                        nrc_aps_content_index
                        .insert_content_units_payload_immutable(
                            db,
                            payload=payload,
                        )
                    )
                else:
                    _fail(
                        "nrc_phase_b_persistence_conflict",
                        "Unknown strict persistence action.",
                    )
            except (
                nrc_aps_content_index.ImmutableContentInsertConflict
            ):
                db.rollback()
                try:
                    recovered = _require_exact_persisted(
                        db,
                        payload=payload,
                    )
                except NrcPhaseBLinkageError as conflict:
                    raise NrcPhaseBLinkageError(
                        "nrc_phase_b_persistence_conflict",
                        "Concurrent persistence was not exact.",
                    ) from conflict
                db.commit()
                return recovered

            exact = _require_exact_persisted(db, payload=payload)
            if (
                exact.aps_content_linkage_id
                != inserted.aps_content_linkage_id
            ):
                _fail(
                    "nrc_phase_b_persistence_conflict",
                    "Precommit exact-one requery changed linkage identity.",
                )
            db.commit()
            return exact
    except StableRawStorageError as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_raw_drift",
            "Final locked raw snapshot changed during persistence.",
        ) from exc


def bind_strict_nrc_phase_b_linkage(
    db: Session,
    *,
    connector_run_target_id: str,
) -> ApsContentLinkage:
    """Own one clean transaction for strict NRC Phase-B linkage."""

    _require_owned_clean_transaction(db)
    try:
        linkage = _bind_strict_nrc_phase_b_linkage_owned(
            db,
            connector_run_target_id=connector_run_target_id,
        )
        if db.in_transaction():
            _fail(
                "nrc_phase_b_transaction_leak",
                "Owned Phase-B transaction remained active on return.",
            )
        return linkage
    except Exception:
        if db.in_transaction():
            db.rollback()
        raise
